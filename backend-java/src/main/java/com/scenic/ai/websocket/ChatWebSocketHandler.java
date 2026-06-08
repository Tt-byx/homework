package com.scenic.ai.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Component
@Slf4j
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();
    private final Map<String, byte[]> pendingAudio = new ConcurrentHashMap<>();

    @Autowired
    private ObjectMapper objectMapper;

    @Value("${python.backend.url:http://localhost:8000}")
    private String pythonBackendUrl;

    private final HttpClient httpClient = HttpClient.newBuilder().build();
    private final ExecutorService executor = Executors.newCachedThreadPool();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.put(session.getId(), session);
        log.info("WebSocket 连接建立: {}", session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        String payload = message.getPayload();
        log.debug("收到文本消息: {}", payload.length() > 200 ? payload.substring(0, 200) + "..." : payload);

        try {
            WebSocketMessage msg = objectMapper.readValue(payload, WebSocketMessage.class);

            switch (msg.getType()) {
                case "text":
                    handleTextChat(session, msg);
                    break;
                case "audio":
                    // 音频元数据，标记此 session 下一条二进制帧为音频数据
                    pendingAudio.put(session.getId(), new byte[0]);
                    log.info("收到音频元数据，等待音频二进制帧: session={}", session.getId());
                    break;
                default:
                    log.warn("未知消息类型: {}", msg.getType());
                    sendToClient(session, WebSocketMessage.error("未知消息类型: " + msg.getType()));
            }
        } catch (Exception e) {
            log.error("解析消息失败: {}", e.getMessage(), e);
            trySendToClient(session, WebSocketMessage.error("消息格式错误"));
        }
    }

    @Override
    protected void handleBinaryMessage(WebSocketSession session, BinaryMessage message) {
        ByteBuffer buffer = message.getPayload();
        byte[] audioData = new byte[buffer.remaining()];
        buffer.get(audioData);

        log.info("收到音频二进制帧: {} bytes, session={}", audioData.length, session.getId());

        // 异步转发到 Python 后端
        CompletableFuture.runAsync(() -> proxyAudioToPython(session, audioData), executor);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session.getId());
        pendingAudio.remove(session.getId());
        log.info("WebSocket 连接关闭: {}", session.getId());
    }

    /**
     * 处理文字对话：转发到 Python SSE 端点，流式回传给前端
     */
    private void handleTextChat(WebSocketSession session, WebSocketMessage msg) {
        CompletableFuture.runAsync(() -> {
            try {
                // 构建 multipart/form-data 请求到 Python /api/chat/stream
                String boundary = "----WebKitFormBoundary" + System.currentTimeMillis();
                String body = buildMultipartBody(boundary, msg.getContent(), msg.getSessionId());

                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(pythonBackendUrl + "/api/chat/stream"))
                        .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                        .POST(HttpRequest.BodyPublishers.ofString(body))
                        .build();

                // 发送请求并处理 SSE 流
                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

                // 解析 SSE 响应并转发给前端
                processSSEResponse(session, response.body());

            } catch (Exception e) {
                log.error("转发文字消息到 Python 失败: {}", e.getMessage(), e);
                trySendToClient(session, WebSocketMessage.error("AI服务暂时不可用"));
            }
        }, executor);
    }

    /**
     * 处理音频对话：转发音频到 Python SSE 端点
     */
    private void proxyAudioToPython(WebSocketSession session, byte[] audioData) {
        try {
            // 构建 multipart/form-data 请求（包含音频文件）
            String boundary = "----WebKitFormBoundary" + System.currentTimeMillis();
            String sessionId = null; // 可从 pendingAudio 中获取元数据
            byte[] body = buildMultipartAudioBody(boundary, audioData, sessionId);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(pythonBackendUrl + "/api/chat/stream"))
                    .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                    .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            processSSEResponse(session, response.body());

        } catch (Exception e) {
            log.error("转发音频到 Python 失败: {}", e.getMessage(), e);
            trySendToClient(session, WebSocketMessage.error("语音处理失败"));
        }
    }

    /**
     * 解析 SSE 响应并转发给前端客户端
     */
    private void processSSEResponse(WebSocketSession session, String sseBody) {
        String[] lines = sseBody.split("\n");
        String currentEvent = "";

        for (String line : lines) {
            line = line.trim();
            if (line.startsWith("event: ")) {
                currentEvent = line.substring(7).trim();
            } else if (line.startsWith("data: ")) {
                String data = line.substring(6).trim();
                try {
                    // 根据事件类型转发
                    switch (currentEvent) {
                        case "text_chunk":
                            Map<String, Object> textData = objectMapper.readValue(data, Map.class);
                            sendToClient(session, WebSocketMessage.textChunk((String) textData.get("text")));
                            break;
                        case "audio_chunk":
                            Map<String, Object> audioData = objectMapper.readValue(data, Map.class);
                            sendToClient(session, WebSocketMessage.audioChunk(
                                    (String) audioData.get("audio"),
                                    (String) audioData.get("format")
                            ));
                            break;
                        case "asr_result":
                            Map<String, Object> asrData = objectMapper.readValue(data, Map.class);
                            sendToClient(session, WebSocketMessage.asrResult((String) asrData.get("text")));
                            break;
                        case "done":
                            Map<String, Object> doneData = objectMapper.readValue(data, Map.class);
                            sendToClient(session, WebSocketMessage.done(
                                    (String) doneData.get("session_id"),
                                    (String) doneData.get("total_text")
                            ));
                            break;
                        case "error":
                            Map<String, Object> errData = objectMapper.readValue(data, Map.class);
                            sendToClient(session, WebSocketMessage.error((String) errData.get("message")));
                            break;
                    }
                } catch (Exception e) {
                    log.error("解析 SSE 数据失败: {}", data, e);
                }
            }
        }
    }

    /**
     * 构建 multipart/form-data 文本请求体
     */
    private String buildMultipartBody(String boundary, String message, String sessionId) {
        StringBuilder sb = new StringBuilder();
        sb.append("--").append(boundary).append("\r\n");
        sb.append("Content-Disposition: form-data; name=\"message\"\r\n\r\n");
        sb.append(message).append("\r\n");

        if (sessionId != null) {
            sb.append("--").append(boundary).append("\r\n");
            sb.append("Content-Disposition: form-data; name=\"session_id\"\r\n\r\n");
            sb.append(sessionId).append("\r\n");
        }

        sb.append("--").append(boundary).append("--\r\n");
        return sb.toString();
    }

    /**
     * 构建 multipart/form-data 音频请求体
     */
    private byte[] buildMultipartAudioBody(String boundary, byte[] audioData, String sessionId) {
        StringBuilder header = new StringBuilder();
        header.append("--").append(boundary).append("\r\n");
        header.append("Content-Disposition: form-data; name=\"audio\"; filename=\"audio.webm\"\r\n");
        header.append("Content-Type: audio/webm\r\n\r\n");

        byte[] headerBytes = header.toString().getBytes();

        String footer = "\r\n--" + boundary + "--\r\n";
        byte[] footerBytes = footer.getBytes();

        // 合并 header + audioData + footer
        byte[] result = new byte[headerBytes.length + audioData.length + footerBytes.length];
        System.arraycopy(headerBytes, 0, result, 0, headerBytes.length);
        System.arraycopy(audioData, 0, result, headerBytes.length, audioData.length);
        System.arraycopy(footerBytes, 0, result, headerBytes.length + audioData.length, footerBytes.length);

        return result;
    }

    /**
     * 发送消息给客户端
     */
    private void sendToClient(WebSocketSession session, WebSocketMessage msg) {
        try {
            String json = objectMapper.writeValueAsString(msg);
            synchronized (session) {
                if (session.isOpen()) {
                    session.sendMessage(new TextMessage(json));
                }
            }
        } catch (IOException e) {
            log.error("发送消息给客户端失败: {}", e.getMessage());
        }
    }

    /**
     * 安全发送（捕获异常不抛出）
     */
    private void trySendToClient(WebSocketSession session, WebSocketMessage msg) {
        try {
            sendToClient(session, msg);
        } catch (Exception e) {
            log.error("发送消息异常: {}", e.getMessage());
        }
    }
}
