"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle, XCircle, ArrowUp, DollarSign, MapPin, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

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

interface AMLReviewCardProps {
  review: AMLReview;
  onApprove: () => void;
  onReject: () => void;
  onEscalate: () => void;
  loading?: boolean;
}

export function AMLReviewCard({
  review,
  onApprove,
  onReject,
  onEscalate,
  loading,
}: AMLReviewCardProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "HIGH":
        return "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/50";
      case "MEDIUM":
        return "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-500/50";
      case "LOW":
        return "bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/50";
      default:
        return "bg-gray-500/20 text-gray-700 dark:text-gray-400 border-gray-500/50";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "bg-green-500/20 text-green-700 dark:text-green-400";
      case "rejected":
        return "bg-red-500/20 text-red-700 dark:text-red-400";
      case "escalated":
        return "bg-orange-500/20 text-orange-700 dark:text-orange-400";
      default:
        return "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400";
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), "MMM dd, yyyy HH:mm");
    } catch {
      return dateString;
    }
  };

  return (
    <Card className={cn("relative", review.status !== "pending" && "opacity-75")}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-sm font-medium mb-2">
              Transaction {review.transaction_id.slice(0, 8)}...
            </CardTitle>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className={cn("text-xs", getSeverityColor(review.anomalies.severity))}>
                {review.anomalies.severity} Severity
              </Badge>
              <Badge variant="outline" className={cn("text-xs", getStatusColor(review.status))}>
                {review.status.toUpperCase()}
              </Badge>
              {review.risk_score !== undefined && (
                <Badge variant="outline" className="text-xs">
                  Risk: {review.risk_score}/100
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Transaction Details */}
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">
              {review.amount.toLocaleString()} {review.currency}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              {review.origin} → {review.destination}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">{formatDate(review.timestamp)}</span>
          </div>
          <div className="text-xs text-muted-foreground">
            Customer: {review.customer_id.slice(0, 8)}...
          </div>
        </div>

        {/* Anomalies */}
        {review.anomalies.anomalies_detected && (
          <div className="rounded-md border border-border bg-muted/30 p-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
              <span className="text-xs font-semibold uppercase tracking-wider">
                Anomalies Detected
              </span>
            </div>
            <div className="space-y-1">
              {review.anomalies.anomaly_types && review.anomalies.anomaly_types.length > 0 ? (
                <ul className="text-xs space-y-1">
                  {review.anomalies.anomaly_types.map((type, idx) => (
                    <li key={idx} className="text-muted-foreground">
                      • {type}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-xs text-muted-foreground">No specific anomalies listed</div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        {review.status === "pending" && (
          <div className="flex flex-col gap-2 pt-2 border-t border-border">
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={onApprove}
                disabled={loading}
                className="flex-1 bg-green-600 text-white hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                Approve
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={onReject}
                disabled={loading}
                className="flex-1"
              >
                <XCircle className="h-4 w-4 mr-1" />
                Reject
              </Button>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={onEscalate}
              disabled={loading}
              className="w-full"
            >
              <ArrowUp className="h-4 w-4 mr-1" />
              Escalate
            </Button>
          </div>
        )}

        {/* Status Message */}
        {review.status !== "pending" && (
          <div className="pt-2 border-t border-border">
            <div className={cn("text-xs font-medium", getStatusColor(review.status))}>
              {review.status === "approved" && "✓ Transaction approved"}
              {review.status === "rejected" && "✗ Transaction rejected"}
              {review.status === "escalated" && "↑ Escalated for review"}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
