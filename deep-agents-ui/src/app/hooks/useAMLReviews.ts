"use client";

import { useState, useEffect, useCallback } from "react";

interface AMLReview {
  transaction_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  origin: string;
  destination: string;
  transaction_type: string;
  timestamp: string;
  description?: string;
  anomalies: {
    anomalies_detected: boolean;
    anomaly_types: string[];
    severity: "LOW" | "MEDIUM" | "HIGH";
    details: string;
  };
  risk_score?: number;
  alert_id?: string;
  status: "pending" | "approved" | "rejected" | "escalated";
}

export function useAMLReviews(apiUrl: string) {
  const [reviews, setReviews] = useState<AMLReview[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    if (!apiUrl) return;

    setLoading(true);
    setError(null);

    try {
      // In a real implementation, you'd have an endpoint to fetch pending reviews
      // For now, we'll simulate by checking LangGraph threads with interrupts
      // or create a new endpoint in FastAPI
      const response = await fetch(`${apiUrl}/aml/reviews/pending`);
      
      if (!response.ok) {
        // If endpoint doesn't exist, return empty array (will be handled by backend)
        if (response.status === 404) {
          setReviews([]);
          return;
        }
        throw new Error(`Failed to fetch reviews: ${response.statusText}`);
      }

      const data = await response.json();
      setReviews(data.reviews || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch reviews");
      setReviews([]);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  const approveReview = useCallback(
    async (transactionId: string) => {
      setLoading(true);
      try {
        const response = await fetch(`${apiUrl}/aml/reviews/${transactionId}/approve`, {
          method: "POST",
        });
        if (!response.ok) throw new Error("Failed to approve");
        await fetchReviews();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to approve review");
      } finally {
        setLoading(false);
      }
    },
    [apiUrl, fetchReviews]
  );

  const rejectReview = useCallback(
    async (transactionId: string) => {
      setLoading(true);
      try {
        const response = await fetch(`${apiUrl}/aml/reviews/${transactionId}/reject`, {
          method: "POST",
        });
        if (!response.ok) throw new Error("Failed to reject");
        await fetchReviews();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to reject review");
      } finally {
        setLoading(false);
      }
    },
    [apiUrl, fetchReviews]
  );

  const escalateReview = useCallback(
    async (transactionId: string) => {
      setLoading(true);
      try {
        const response = await fetch(`${apiUrl}/aml/reviews/${transactionId}/escalate`, {
          method: "POST",
        });
        if (!response.ok) throw new Error("Failed to escalate");
        await fetchReviews();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to escalate review");
      } finally {
        setLoading(false);
      }
    },
    [apiUrl, fetchReviews]
  );

  useEffect(() => {
    fetchReviews();
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchReviews, 5000);
    return () => clearInterval(interval);
  }, [fetchReviews]);

  return {
    reviews,
    loading,
    error,
    refreshReviews: fetchReviews,
    approveReview,
    rejectReview,
    escalateReview,
  };
}
