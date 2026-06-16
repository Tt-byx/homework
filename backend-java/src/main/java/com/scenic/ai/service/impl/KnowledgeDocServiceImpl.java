package com.scenic.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.scenic.ai.entity.KnowledgeDoc;
import com.scenic.ai.mapper.KnowledgeDocMapper;
import com.scenic.ai.service.KnowledgeDocService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class KnowledgeDocServiceImpl implements KnowledgeDocService {

    private static final Logger log = LoggerFactory.getLogger(KnowledgeDocServiceImpl.class);

    @Autowired
    private KnowledgeDocMapper knowledgeDocMapper;

    @Autowired
    private org.springframework.web.client.RestTemplate restTemplate;

    @Value("${scenic.upload.dir}")
    private String uploadDir;

    @Value("${python.backend.url}")
    private String pythonBackendUrl;

    @Override
    public KnowledgeDoc upload(String title, MultipartFile file) {
        // 1. 保存文件到磁盘
        String originalFilename = fixFilenameEncoding(file.getOriginalFilename());
        String fileType = getFileExtension(originalFilename);
        String savedFileName = UUID.randomUUID() + "." + fileType;
        String filePath = uploadDir + "/" + savedFileName;

        File dir = new File(uploadDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        try {
            file.transferTo(new File(filePath));
        } catch (IOException e) {
            throw new RuntimeException("文件保存失败: " + e.getMessage(), e);
        }

        // 2. 创建数据库记录
        KnowledgeDoc doc = new KnowledgeDoc();
        doc.setTitle(title);
        doc.setFileName(originalFilename);
        doc.setFileUrl(filePath);
        doc.setFileType(fileType);
        doc.setVectorStatus(1); // 处理中
        doc.setStatus(1);
        doc.setCreatedAt(LocalDateTime.now());
        doc.setUpdatedAt(LocalDateTime.now());
        knowledgeDocMapper.insert(doc);

        // 3. 异步调用 Python 处理
        processDocumentAsync(doc.getId(), filePath, fileType, title);

        return doc;
    }

    @Override
    public List<KnowledgeDoc> listAll() {
        return knowledgeDocMapper.selectList(
                new LambdaQueryWrapper<KnowledgeDoc>()
                        .eq(KnowledgeDoc::getStatus, 1)
                        .orderByDesc(KnowledgeDoc::getCreatedAt)
        );
    }

    @Override
    public void delete(Long id) {
        KnowledgeDoc doc = knowledgeDocMapper.selectById(id);
        if (doc == null) {
            throw new RuntimeException("文档不存在: " + id);
        }

        // 软删除
        doc.setStatus(0);
        doc.setUpdatedAt(LocalDateTime.now());
        knowledgeDocMapper.updateById(doc);

        // 删除向量
        try {
            restTemplate.delete(pythonBackendUrl + "/api/knowledge/" + id);
        } catch (Exception e) {
            log.warn("删除向量失败（不影响软删除）: {}", e.getMessage());
        }
    }

    @Override
    public void reprocess(Long id) {
        KnowledgeDoc doc = knowledgeDocMapper.selectById(id);
        if (doc == null) {
            throw new RuntimeException("文档不存在: " + id);
        }

        doc.setVectorStatus(1); // 处理中
        doc.setUpdatedAt(LocalDateTime.now());
        knowledgeDocMapper.updateById(doc);

        processDocumentAsync(doc.getId(), doc.getFileUrl(), doc.getFileType(), doc.getTitle());
    }

    @Async
    public void processDocumentAsync(Long docId, String filePath, String fileType, String docTitle) {
        log.info("开始异步处理文档: id={}, path={}", docId, filePath);
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("doc_id", docId);
            request.put("file_path", filePath);
            request.put("file_type", fileType);
            request.put("doc_title", docTitle);

            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.postForObject(
                    pythonBackendUrl + "/api/knowledge/process",
                    request, Map.class
            );

            int chunkCount = ((Number) response.get("chunk_count")).intValue();
            KnowledgeDoc doc = knowledgeDocMapper.selectById(docId);
            if (doc != null) {
                doc.setVectorStatus(2); // 完成
                doc.setChunkCount(chunkCount);
                doc.setUpdatedAt(LocalDateTime.now());
                knowledgeDocMapper.updateById(doc);
            }
            log.info("文档处理完成: id={}, chunkCount={}", docId, chunkCount);
        } catch (Exception e) {
            log.error("文档处理失败: id={}, error={}", docId, e.getMessage());
            KnowledgeDoc doc = knowledgeDocMapper.selectById(docId);
            if (doc != null) {
                doc.setVectorStatus(3); // 失败
                doc.setUpdatedAt(LocalDateTime.now());
                knowledgeDocMapper.updateById(doc);
            }
        }
    }

    private String getFileExtension(String filename) {
        if (filename == null || !filename.contains(".")) {
            return "unknown";
        }
        return filename.substring(filename.lastIndexOf(".") + 1).toLowerCase();
    }

    /**
     * 修复文件名中文乱码：ISO-8859-1 → UTF-8
     */
    private String fixFilenameEncoding(String filename) {
        if (filename == null) return null;
        try {
            byte[] bytes = filename.getBytes("ISO-8859-1");
            String decoded = new String(bytes, "UTF-8");
            // 只有解码后包含中文字符才认为修复成功
            if (decoded.matches(".*[\\u4e00-\\u9fa5].*")) {
                return decoded;
            }
        } catch (Exception ignored) {}
        return filename;
    }
}
