import { Badge } from '@/components/atoms/Badge';

type Severity = 'high' | 'medium' | 'low';

const variantMap: Record<Severity, 'destructive' | 'warning' | 'success'> = {
  high: 'destructive',
  medium: 'warning',
  low: 'success',
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge variant={variantMap[severity]}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </Badge>
  );
}
