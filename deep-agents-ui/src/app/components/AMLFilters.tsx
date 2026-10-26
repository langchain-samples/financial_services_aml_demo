"use client";

import React from "react";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";

interface Filters {
  severity: "all" | "LOW" | "MEDIUM" | "HIGH";
  status: "all" | "pending" | "approved" | "rejected" | "escalated";
  minAmount: string;
  maxAmount: string;
}

interface AMLFiltersProps {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
}

export function AMLFilters({ filters, onFiltersChange }: AMLFiltersProps) {
  const updateFilter = (key: keyof Filters, value: string) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div>
        <Label htmlFor="severity" className="text-xs font-medium mb-2 block">
          Severity
        </Label>
        <Select value={filters.severity} onValueChange={(v) => updateFilter("severity", v)}>
          <SelectTrigger id="severity" className="h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severities</SelectItem>
            <SelectItem value="HIGH">High</SelectItem>
            <SelectItem value="MEDIUM">Medium</SelectItem>
            <SelectItem value="LOW">Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="status" className="text-xs font-medium mb-2 block">
          Status
        </Label>
        <Select value={filters.status} onValueChange={(v) => updateFilter("status", v)}>
          <SelectTrigger id="status" className="h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="escalated">Escalated</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="minAmount" className="text-xs font-medium mb-2 block">
          Min Amount
        </Label>
        <Input
          id="minAmount"
          type="number"
          placeholder="0"
          value={filters.minAmount}
          onChange={(e) => updateFilter("minAmount", e.target.value)}
          className="h-9"
        />
      </div>

      <div>
        <Label htmlFor="maxAmount" className="text-xs font-medium mb-2 block">
          Max Amount
        </Label>
        <Input
          id="maxAmount"
          type="number"
          placeholder="∞"
          value={filters.maxAmount}
          onChange={(e) => updateFilter("maxAmount", e.target.value)}
          className="h-9"
        />
      </div>
    </div>
  );
}
