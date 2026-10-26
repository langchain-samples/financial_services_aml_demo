"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { AlertCircle, CheckCircle, XCircle, TrendingUp, Filter, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { AMLReviewCard } from "@/app/components/AMLReviewCard";
import { AMLFilters } from "@/app/components/AMLFilters";
import { useAMLReviews } from "@/app/hooks/useAMLReviews";
import { cn } from "@/lib/utils";

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

export default function AMLReviewsPage() {
  const [apiUrl, setApiUrl] = useState<string>("http://localhost:8000");
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    severity: "all" as "all" | "LOW" | "MEDIUM" | "HIGH",
    status: "all" as "all" | "pending" | "approved" | "rejected" | "escalated",
    minAmount: "",
    maxAmount: "",
  });

  const {
    reviews,
    loading,
    error,
    refreshReviews,
    approveReview,
    rejectReview,
    escalateReview,
  } = useAMLReviews(apiUrl);

  // Load API URL from localStorage or env
  useEffect(() => {
    const stored = localStorage.getItem("aml-api-url");
    if (stored) {
      setApiUrl(stored);
    } else if (process.env.NEXT_PUBLIC_API_URL) {
      setApiUrl(process.env.NEXT_PUBLIC_API_URL);
    }
  }, []);

  const saveApiUrl = () => {
    localStorage.setItem("aml-api-url", apiUrl);
  };

  const filteredReviews = reviews.filter((review) => {
    if (filters.severity !== "all" && review.anomalies.severity !== filters.severity) {
      return false;
    }
    if (filters.status !== "all" && review.status !== filters.status) {
      return false;
    }
    if (filters.minAmount && review.amount < parseFloat(filters.minAmount)) {
      return false;
    }
    if (filters.maxAmount && review.amount > parseFloat(filters.maxAmount)) {
      return false;
    }
    return true;
  });

  const pendingCount = reviews.filter((r) => r.status === "pending").length;
  const highSeverityCount = reviews.filter(
    (r) => r.anomalies.severity === "HIGH" && r.status === "pending"
  ).length;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex h-16 items-center justify-between border-b border-border px-6">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <h1 className="text-xl font-semibold">AML Transaction Reviews</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              {pendingCount} Pending
            </span>
            {highSeverityCount > 0 && (
              <span className="flex items-center gap-1 text-destructive">
                <TrendingUp className="h-4 w-4" />
                {highSeverityCount} High Severity
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              onBlur={saveApiUrl}
              placeholder="API URL"
              className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </Button>
            <Button variant="outline" size="sm" onClick={refreshReviews} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        </div>
      </header>

      {showFilters && (
        <div className="border-b border-border bg-muted/30 px-6 py-4">
          <AMLFilters filters={filters} onFiltersChange={setFilters} />
        </div>
      )}

      {error && (
        <div className="mx-6 mt-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <div>
              <div className="font-semibold">Error loading reviews</div>
              <div className="text-sm">{error}</div>
            </div>
          </Alert>
        </div>
      )}

      <main className="flex-1 overflow-y-auto p-6">
        {loading && reviews.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-muted-foreground">Loading reviews...</div>
          </div>
        ) : filteredReviews.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <div className="text-lg font-semibold">No reviews found</div>
              <div className="text-sm text-muted-foreground mt-2">
                {reviews.length === 0
                  ? "No pending reviews. Generate some anomaly transactions to see reviews here."
                  : "No reviews match the current filters."}
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredReviews.map((review) => (
              <AMLReviewCard
                key={review.transaction_id}
                review={review}
                onApprove={() => approveReview(review.transaction_id)}
                onReject={() => rejectReview(review.transaction_id)}
                onEscalate={() => escalateReview(review.transaction_id)}
                loading={loading}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
