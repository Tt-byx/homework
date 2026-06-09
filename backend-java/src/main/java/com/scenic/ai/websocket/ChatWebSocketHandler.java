package com.scenic.ai.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
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
    private final Map<String, String> pendingAudioSessionId = new ConcurrentHashMap<>();
    private final Map<String, String> pendingAudioFormat = new ConcurrentHashMap<>();

    @Autowired
    private ObjectMapper objectMapper;

    @Value("${python.backend.url:http://localhost:8000}")
    private String pythonBackendUrl;

    @Autowired
    private RestTemplate restTemplate;
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
                    // 音频元数据，保存 session_id 和 format，等待二进制帧
                    pendingAudio.put(session.getId(), new byte[0]);
                    pendingAudioSessionId.put(session.getId(), msg.getSessionId());
                    pendingAudioFormat.put(session.getId(), msg.getFormat() != null ? msg.getFormat() : "webm");
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
        pendingAudioSessionId.remove(session.getId());
        pendingAudioFormat.remove(session.getId());
        log.info("WebSocket 连接关闭: {}", session.getId());
    }

    /**
     * 处理文字对话：用 RestTemplate 调 Python /api/chat (JSON)
     */
    private void handleTextChat(WebSocketSession session, WebSocketMessage msg) {
        CompletableFuture.runAsync(() -> {
            try {
                Map<String, Object> requestBody = new java.util.HashMap<>();
                requestBody.put("message", msg.getContent());
                if (msg.getSessionId() != null) {
                    requestBody.put("session_id", msg.getSessionId());
                }

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

                log.info("转发文字消息到 Python: {}", msg.getContent().length() > 50
                        ? msg.getContent().substring(0, 50) + "..." : msg.getContent());

                ResponseEntity<Map> response = restTemplate.exchange(
                        pythonBackendUrl + "/api/chat",
                        HttpMethod.POST,
                        entity,
                        Map.class
                );

                if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                    Map<String, Object> result = response.getBody();
                    String reply = (String) result.get("reply");
                    String sessionId = (String) result.get("session_id");
                    String audio = (String) result.get("audio");

                    // 发送文字
                    sendToClient(session, WebSocketMessage.textChunk(reply));

                    // 发送音频（如果有）
                    if (audio != null && !audio.isEmpty()) {
                        sendToClient(session, WebSocketMessage.audioChunk(audio, "wav"));
                    }

                    // 发送完成标记
                    sendToClient(session, WebSocketMessage.done(sessionId, reply));
                } else {
                    log.error("Python 返回错误: {}", response.getStatusCode());
                    trySendToClient(session, WebSocketMessage.error("AI服务返回错误"));
                }

            } catch (Exception e) {
                log.error("转发文字消息到 Python 失败: {}", e.getMessage(), e);
                trySendToClient(session, WebSocketMessage.error("AI服务暂时不可用"));
            }
        }, executor);
    }

    /**
     * 处理音频对话：用 RestTemplate 转发音频到 Python /api/chat/stream
     */
    private void proxyAudioToPython(WebSocketSession session, byte[] audioData) {
        try {
            String sessionId = pendingAudioSessionId.remove(session.getId());
            String rawFormat = pendingAudioFormat.remove(session.getId());
            final String audioFormat = rawFormat != null ? rawFormat : "webm";

            // 构建 multipart 请求
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            org.springframework.util.LinkedMultiValueMap<String, Object> body = new org.springframework.util.LinkedMultiValueMap<>();
            body.add("audio", new org.springframework.core.io.ByteArrayResource(audioData) {
                @Override
                public String getFilename() {
                    return "audio." + audioFormat;
                }
            });
            if (sessionId != null) {
                body.add("session_id", sessionId);
            }

            HttpEntity<org.springframework.util.LinkedMultiValueMap<String, Object>> entity = new HttpEntity<>(body, headers);

            log.info("转发音频到 Python: {} bytes, format={}", audioData.length, audioFormat);

            ResponseEntity<String> response = restTemplate.exchange(
                    pythonBackendUrl + "/api/chat/stream",
                    HttpMethod.POST,
                    entity,
                    String.class
            );

            if (response.getBody() != null) {
                processSSEResponse(session, response.getBody());
            } else {
                trySendToClient(session, WebSocketMessage.error("语音处理返回空"));
            }

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
