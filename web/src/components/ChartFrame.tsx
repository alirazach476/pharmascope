import type { ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

export function ChartFrame({
  children,
  empty,
  emptyMessage = "No data available in this deployment snapshot.",
}: {
  children: ReactNode;
  empty?: boolean;
  emptyMessage?: string;
}) {
  if (empty) {
    return <div className="chart-empty">{emptyMessage}</div>;
  }
  return (
    <ResponsiveContainer width="100%" height="100%">
      {children as React.ReactElement}
    </ResponsiveContainer>
  );
}
