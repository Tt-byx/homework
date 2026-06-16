package com.scenic.ai.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.scenic.ai.dto.Result;
import com.scenic.ai.entity.ChatMessage;
import com.scenic.ai.entity.Conversation;
import com.scenic.ai.mapper.ChatMessageMapper;
import com.scenic.ai.mapper.ConversationMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/conversations")
public class ConversationController {

    @Autowired
    private ConversationMapper conversationMapper;

    @Autowired
    private ChatMessageMapper chatMessageMapper;

    @GetMapping
    public Result<List<Conversation>> list(
            @RequestHeader(value = "Authorization", required = false) String auth) {
        Long userId = AuthController.getUserIdFromToken(extractToken(auth));
        if (userId == null) {
            return Result.error(401, "未登录");
        }

        List<Conversation> conversations = conversationMapper.selectList(
                new LambdaQueryWrapper<Conversation>()
                        .eq(Conversation::getUserId, userId)
                        .eq(Conversation::getStatus, 1)
                        .orderByDesc(Conversation::getUpdatedAt));

        return Result.success(conversations);
    }

    @GetMapping("/{id}/messages")
    public Result<List<ChatMessage>> messages(
            @PathVariable Long id,
            @RequestHeader(value = "Authorization", required = false) String auth) {
        Long userId = AuthController.getUserIdFromToken(extractToken(auth));
        if (userId == null) {
            return Result.error(401, "未登录");
        }

        // 验证对话属于该用户
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

    private String extractToken(String auth) {
        if (auth != null && auth.startsWith("Bearer ")) {
            return auth.substring(7);
        }
        return null;
    }
}
