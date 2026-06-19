package com.scenic.ai.service;

import java.util.Map;

public interface AnalyticsService {
    Map<String, Object> importXlsx(String filePath) throws Exception;
    Map<String, Object> getConsumptionTrend();
    Map<String, Object> getVisitorProfile();
    Map<String, Object> getSatisfactionDistribution();
    Map<String, Object> getPeakPeriods();
    Map<String, Object> getTopAttractions();
}
