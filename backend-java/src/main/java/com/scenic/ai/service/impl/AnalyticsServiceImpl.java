package com.scenic.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.scenic.ai.entity.TourismData;
import com.scenic.ai.mapper.TourismDataMapper;
import com.scenic.ai.service.AnalyticsService;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.math.BigDecimal;
import java.sql.Date;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;

@Service
@Slf4j
public class AnalyticsServiceImpl implements AnalyticsService {

    @Autowired
    private TourismDataMapper tourismDataMapper;

    @Value("${upload.dir:D:/scenic_uploads}")
    private String uploadDir;

    @Override
    public Map<String, Object> importXlsx(String filePath) throws Exception {
        // 查找文件：优先指定路径，然后项目根目录，最后上传目录
        File file = null;
        if (filePath != null && !filePath.isEmpty()) {
            file = new File(filePath);
        }
        if (file == null || !file.exists()) {
            file = new File("景点景区旅游数据行为分析数据.xlsx");
        }
        if (!file.exists()) {
            file = new File(uploadDir, "景点景区旅游数据行为分析数据.xlsx");
        }
        if (!file.exists()) {
            throw new FileNotFoundException("找不到 xlsx 文件，请将文件放在项目根目录或上传目录: " + uploadDir);
        }

        log.info("开始导入 xlsx: {}", file.getAbsolutePath());

        // 清空旧数据
        tourismDataMapper.delete(null);

        int totalRows = 0;
        int batch_size = 500;
        List<TourismData> batch = new ArrayList<>();

        try (Workbook workbook = new XSSFWorkbook(new FileInputStream(file))) {
            Sheet sheet = workbook.getSheetAt(0);
            Iterator<Row> rowIterator = sheet.iterator();

            // 跳过表头
            if (rowIterator.hasNext()) {
                rowIterator.next();
            }

            while (rowIterator.hasNext()) {
                Row row = rowIterator.next();
                TourismData data = parseRow(row);
                if (data != null) {
                    batch.add(data);
                    if (batch.size() >= batch_size) {
                        batchInsert(batch);
                        totalRows += batch.size();
                        batch.clear();
                    }
                }
            }

            // 插入剩余
            if (!batch.isEmpty()) {
                batchInsert(batch);
                totalRows += batch.size();
            }
        }

        Map<String, Object> result = new HashMap<>();
        result.put("totalRows", totalRows);
        result.put("message", "导入成功");
        log.info("xlsx 导入完成: {} 条记录", totalRows);
        return result;
    }

    private TourismData parseRow(Row row) {
        try {
            TourismData data = new TourismData();
            data.setTouristId(getCellString(row, 0));
            data.setNickname(getCellString(row, 1));
            data.setAge(getCellInt(row, 2));
            data.setGender(getCellString(row, 3));
            data.setAttractionName(getCellString(row, 4));
            // col 5 = attraction_content (跳过，太长)
            data.setAttractionType(getCellString(row, 6));
            data.setVisitDate(getCellDate(row, 7));
            data.setStayDuration(getCellDecimal(row, 8));
            data.setTicketCost(getCellDecimal(row, 9));
            data.setFoodCost(getCellDecimal(row, 10));
            data.setShoppingCost(getCellDecimal(row, 11));
            data.setTransportCost(getCellDecimal(row, 12));
            data.setEntertainmentCost(getCellDecimal(row, 13));
            data.setTotalCost(getCellDecimal(row, 14));
            data.setGroupSize(getCellInt(row, 15));
            data.setSatisfaction(getCellDecimal(row, 16));
            data.setCreatedAt(LocalDateTime.now());
            return data;
        } catch (Exception e) {
            log.debug("跳过无效行 {}: {}", row.getRowNum(), e.getMessage());
            return null;
        }
    }

    private void batchInsert(List<TourismData> batch) {
        for (TourismData data : batch) {
            tourismDataMapper.insert(data);
        }
    }

    private String getCellString(Row row, int col) {
        Cell cell = row.getCell(col);
        if (cell == null) return "";
        if (cell.getCellType() == CellType.NUMERIC) {
            return String.valueOf((long) cell.getNumericCellValue());
        }
        return cell.toString().trim();
    }

    private Integer getCellInt(Row row, int col) {
        Cell cell = row.getCell(col);
        if (cell == null) return null;
        if (cell.getCellType() == CellType.NUMERIC) {
            return (int) cell.getNumericCellValue();
        }
        try {
            return Integer.parseInt(cell.toString().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private BigDecimal getCellDecimal(Row row, int col) {
        Cell cell = row.getCell(col);
        if (cell == null) return null;
        if (cell.getCellType() == CellType.NUMERIC) {
            return BigDecimal.valueOf(cell.getNumericCellValue());
        }
        try {
            return new BigDecimal(cell.toString().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private LocalDate getCellDate(Row row, int col) {
        Cell cell = row.getCell(col);
        if (cell == null) return null;
        if (cell.getCellType() == CellType.NUMERIC && DateUtil.isCellDateFormatted(cell)) {
            java.util.Date date = cell.getDateCellValue();
            return date.toInstant().atZone(ZoneId.systemDefault()).toLocalDate();
        }
        try {
            return LocalDate.parse(cell.toString().trim().substring(0, 10));
        } catch (Exception e) {
            return null;
        }
    }

    // ============ 查询统计方法 ============

    @Override
    public Map<String, Object> getConsumptionTrend() {
        List<Map<String, Object>> rows = tourismDataMapper.selectMaps(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TourismData>()
                        .select("DATE_FORMAT(visit_date, '%Y-%m') as month",
                                "AVG(ticket_cost) as avg_ticket",
                                "AVG(food_cost) as avg_food",
                                "AVG(shopping_cost) as avg_shopping",
                                "AVG(transport_cost) as avg_transport",
                                "AVG(entertainment_cost) as avg_entertainment",
                                "AVG(total_cost) as avg_total",
                                "COUNT(*) as count")
                        .groupBy("DATE_FORMAT(visit_date, '%Y-%m')")
                        .orderByAsc("month"));

        Map<String, Object> result = new HashMap<>();
        result.put("data", rows);
        return result;
    }

    @Override
    public Map<String, Object> getVisitorProfile() {
        // 年龄分布
        List<Map<String, Object>> ageDistribution = tourismDataMapper.selectMaps(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TourismData>()
                        .select("CASE " +
                                "  WHEN age < 18 THEN '18岁以下' " +
                                "  WHEN age BETWEEN 18 AND 25 THEN '18-25岁' " +
                                "  WHEN age BETWEEN 26 AND 35 THEN '26-35岁' " +
                                "  WHEN age BETWEEN 36 AND 45 THEN '36-45岁' " +
                                "  WHEN age BETWEEN 46 AND 55 THEN '46-55岁' " +
                                "  ELSE '55岁以上' END as age_group",
                                "COUNT(*) as count")
                        .groupBy("age_group"));

        // 性别分布
        List<Map<String, Object>> genderDistribution = tourismDataMapper.selectMaps(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TourismData>()
                        .select("gender", "COUNT(*) as count")
                        .groupBy("gender"));

        // 团队规模分布
        List<Map<String, Object>> groupDistribution = tourismDataMapper.selectMaps(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TourismData>()
                        .select("group_size", "COUNT(*) as count")
                        .groupBy("group_size")
                        .orderByAsc("group_size"));

        Map<String, Object> result = new HashMap<>();
        result.put("ageDistribution", ageDistribution);
        result.put("genderDistribution", genderDistribution);
        result.put("groupDistribution", groupDistribution);
        return result;
    }

    @Override
    public Map<String, Object> getSatisfactionDistribution() {
        List<Map<String, Object>> rows = tourismDataMapper.selectMaps(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TourismData>()
                        .select("FLOOR(satisfaction) as score", "COUNT(*) as count")
                        .groupBy("FLOOR(satisfaction)")
                        .orderByAsc("score"));

        Map<String, Object> result = new HashMap<>();
        result.put("data", rows);
        return result;
    }

    @Override
    public Map<String, Object> getPeakPeriods() {
        List<Map<String, Object>> rows = tourismDataMapper.selectMaps(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TourismData>()
                        .select("DATE_FORMAT(visit_date, '%Y-%m') as month",
                                "COUNT(*) as visitor_count",
                                "COUNT(DISTINCT tourist_id) as unique_visitors")
                        .groupBy("DATE_FORMAT(visit_date, '%Y-%m')")
                        .orderByAsc("month"));

        Map<String, Object> result = new HashMap<>();
        result.put("data", rows);
        return result;
    }

    @Override
    public Map<String, Object> getTopAttractions() {
        List<Map<String, Object>> rows = tourismDataMapper.selectMaps(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TourismData>()
                        .select("attraction_name", "attraction_type",
                                "COUNT(*) as visit_count",
                                "AVG(satisfaction) as avg_satisfaction",
                                "AVG(total_cost) as avg_cost")
                        .groupBy("attraction_name", "attraction_type")
                        .orderByDesc("visit_count")
                        .last("LIMIT 10"));

        Map<String, Object> result = new HashMap<>();
        result.put("data", rows);
        return result;
    }
}
