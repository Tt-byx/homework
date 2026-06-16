package com.scenic.ai.controller;

import com.scenic.ai.dto.Result;
import com.scenic.ai.entity.KnowledgeDoc;
import com.scenic.ai.service.KnowledgeDocService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/knowledge")
public class KnowledgeDocController {

    @Autowired
    private KnowledgeDocService knowledgeDocService;

    @PostMapping("/upload")
    public Result<KnowledgeDoc> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam("title") String title) {
        KnowledgeDoc doc = knowledgeDocService.upload(title, file);
        return Result.success(doc);
    }

    @GetMapping("/list")
    public Result<List<KnowledgeDoc>> list() {
        return Result.success(knowledgeDocService.listAll());
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        knowledgeDocService.delete(id);
        return Result.success(null);
    }

    @PostMapping("/process/{id}")
    public Result<Void> process(@PathVariable Long id) {
        knowledgeDocService.process(id);
        return Result.success(null);
    }

    @PostMapping("/reprocess/{id}")
    public Result<Void> reprocess(@PathVariable Long id) {
        knowledgeDocService.reprocess(id);
        return Result.success(null);
    }
}
