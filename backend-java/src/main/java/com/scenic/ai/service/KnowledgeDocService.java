package com.scenic.ai.service;

import com.scenic.ai.entity.KnowledgeDoc;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

public interface KnowledgeDocService {

    KnowledgeDoc upload(String title, MultipartFile file);

    List<KnowledgeDoc> listAll();

    void delete(Long id);

    void reprocess(Long id);
}
