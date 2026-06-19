package com.scenic.ai.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.scenic.ai.dto.Result;
import com.scenic.ai.entity.ChatMessage;
import com.scenic.ai.entity.Conversation;
import com.scenic.ai.mapper.ChatMessageMapper;
import com.scenic.ai.mapper.ConversationMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/conversations")
public class ConversationController {

    @Autowired
    private ConversationMapper conversationMapper;

    @Autowired
    private ChatMessageMapper chatMessageMapper;

    /** 获取当前用户的所有对话（按更新时间倒序） */
    @GetMapping
    public Result<List<Conversation>> list(
            @RequestHeader(value = "Authorization", required = false) String auth) {
        Long userId = AuthController.getUserIdFromToken(extractToken(auth));
        if (userId == null) return Result.error(401, "未登录");

        List<Conversation> conversations = conversationMapper.selectList(
                new LambdaQueryWrapper<Conversation>()
                        .eq(Conversation::getUserId, userId)
                        .eq(Conversation::getStatus, 1)
                        .orderByDesc(Conversation::getUpdatedAt));
        return Result.success(conversations);
    }

    /** 获取指定对话的全部消息 */
    @GetMapping("/{id}/messages")
    public Result<List<ChatMessage>> messages(
            @PathVariable Long id,
            @RequestHeader(value = "Authorization", required = false) String auth) {
        Long userId = AuthController.getUserIdFromToken(extractToken(auth));
        if (userId == null) return Result.error(401, "未登录");

        Conversation conv = conversationMapper.selectById(id);
        if (conv == null || !userId.equals(conv.getUserId())) {
            return Result.error(403, "无权访问");
        }

        List<ChatMessage> messages = chatMessageMapper.selectList(
                new LambdaQueryWrapper<ChatMessage>()
                        .eq(ChatMessage::getConversationId, id)
                        .orderByAsc(ChatMessage::getCreatedAt));
        return Result.success(messages);
    }

    /** 删除对话（软删除） */
    @DeleteMapping("/{id}")
    public Result<Void> delete(
            @PathVariable Long id,
            @RequestHeader(value = "Authorization", required = false) String auth) {
        Long userId = AuthController.getUserIdFromToken(extractToken(auth));
        if (userId == null) return Result.error(401, "未登录");

        Conversation conv = conversationMapper.selectById(id);
        if (conv == null || !userId.equals(conv.getUserId())) {
            return Result.error(403, "无权访问");
        }

        conv.setStatus(0);
        conv.setUpdatedAt(LocalDateTime.now());
        conversationMapper.updateById(conv);
        return Result.success(null);
    }

    /** 重命名对话 */
    @PutMapping("/{id}/title")
    public Result<Void> rename(
            @PathVariable Long id,
            @RequestBody Map<String, String> body,
            @RequestHeader(value = "Authorization", required = false) String auth) {
        Long userId = AuthController.getUserIdFromToken(extractToken(auth));
        if (userId == null) return Result.error(401, "未登录");

        Conversation conv = conversationMapper.selectById(id);
        if (conv == null || !userId.equals(conv.getUserId())) {
            return Result.error(403, "无权访问");
        }

        String newTitle = body.get("title");
        if (newTitle == null || newTitle.isBlank()) {
            return Result.error(400, "标题不能为空");
        }

        conv.setTitle(newTitle.trim());
        conv.setUpdatedAt(LocalDateTime.now());
        conversationMapper.updateById(conv);
        return Result.success(null);
    }

    private String extractToken(String auth) {
        if (auth != null && auth.startsWith("Bearer ")) {
            return auth.substring(7);
        }
        return null;
    }
}
