import axios from 'axios';
import {
  HealthResponse,
  MetricsOverview,
  PaginatedPayments,
  PaymentFullDetail,
  RecoveryExecutionResponse
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getHealthStatus = async (): Promise<HealthResponse> => {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
};

export const getMetricsOverview = async (): Promise<MetricsOverview> => {
  const response = await apiClient.get<MetricsOverview>('/metrics/overview');
  return response.data;
};

export const getPayments = async (
  page: number = 1,
  pageSize: number = 20,
  paymentMethod?: string,
  status?: string,
  minAmount?: number
): Promise<PaginatedPayments> => {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (paymentMethod && paymentMethod !== 'all') params.payment_method = paymentMethod;
  if (status && status !== 'all') params.status = status;
  if (minAmount) params.min_amount = minAmount;

  const response = await apiClient.get<PaginatedPayments>('/payments', { params });
  return response.data;
};

export const getPaymentDetail = async (paymentId: string): Promise<PaymentFullDetail> => {
  const response = await apiClient.get<PaymentFullDetail>(`/recovery/${paymentId}`);
  return response.data;
};

export const executeRecovery = async (paymentId: string): Promise<RecoveryExecutionResponse> => {
  const response = await apiClient.post<RecoveryExecutionResponse>(`/recovery/execute?payment_id=${paymentId}`);
  return response.data;
};
