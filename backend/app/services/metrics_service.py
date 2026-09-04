from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.payment import Payment
from app.schemas.metrics import MetricsOverviewResponse, FailureReasonMetric, PaymentMethodMetric

class MetricsService:
    @staticmethod
    def get_metrics_overview(db: Session) -> MetricsOverviewResponse:
        """Calculates macro system metrics directly from database records."""
        total_pmts = db.query(func.count(Payment.id)).scalar() or 0
        total_risk = db.query(func.sum(Payment.amount)).scalar() or 0.0
        avg_amount = db.query(func.avg(Payment.amount)).scalar() or 0.0
        
        # Ground Truth Recovered Metrics (Evaluation Only)
        gt_recovered_revenue = db.query(func.sum(Payment.amount_recovered)).scalar() or 0.0
        gt_recovered_count = db.query(func.count(Payment.id)).filter(Payment.recovered == True).scalar() or 0
        gt_recovery_rate = (gt_recovered_count / total_pmts * 100.0) if total_pmts > 0 else 0.0

        # Count by Failure Reason
        reason_counts_raw = (
            db.query(Payment.failure_reason, func.count(Payment.id))
            .group_by(Payment.failure_reason)
            .all()
        )
        reason_counts = {r: c for r, c in reason_counts_raw}

        # Count by Payment Method
        method_counts_raw = (
            db.query(Payment.payment_method, func.count(Payment.id))
            .group_by(Payment.payment_method)
            .all()
        )
        method_counts = {m: c for m, c in method_counts_raw}

        return MetricsOverviewResponse(
            total_failed_payments=total_pmts,
            total_revenue_at_risk=round(float(total_risk), 2),
            total_payments_count=total_pmts,
            average_payment_amount=round(float(avg_amount), 2),
            ground_truth_recovered_revenue=round(float(gt_recovered_revenue), 2),
            ground_truth_recovery_rate=round(float(gt_recovery_rate), 2),
            payment_count_by_failure_reason=reason_counts,
            payment_count_by_payment_method=method_counts,
        )

    @staticmethod
    def get_failure_reason_metrics(db: Session) -> List[FailureReasonMetric]:
        """Calculates breakdown metrics grouped by failure_reason."""
        records = db.query(Payment.failure_reason, Payment.amount, Payment.recovered).all()
        
        aggregates: Dict[str, Dict] = {}
        for r, amount, recovered in records:
            if r not in aggregates:
                aggregates[r] = {"count": 0, "total_risk": 0.0, "recovered_count": 0}
            aggregates[r]["count"] += 1
            aggregates[r]["total_risk"] += float(amount)
            if recovered:
                aggregates[r]["recovered_count"] += 1

        metrics = []
        for r, data in aggregates.items():
            cnt = data["count"]
            rec_cnt = data["recovered_count"]
            rate = (rec_cnt / cnt * 100.0) if cnt > 0 else 0.0
            metrics.append(
                FailureReasonMetric(
                    failure_reason=r,
                    count=cnt,
                    total_revenue_at_risk=round(data["total_risk"], 2),
                    recovery_rate=round(rate, 2),
                    recovered_count=rec_cnt
                )
            )
        return metrics

    @staticmethod
    def get_payment_method_metrics(db: Session) -> List[PaymentMethodMetric]:
        """Calculates breakdown metrics grouped by payment_method."""
        records = db.query(Payment.payment_method, Payment.amount, Payment.recovered).all()
        
        aggregates: Dict[str, Dict] = {}
        for m, amount, recovered in records:
            if m not in aggregates:
                aggregates[m] = {"count": 0, "total_risk": 0.0, "recovered_count": 0}
            aggregates[m]["count"] += 1
            aggregates[m]["total_risk"] += float(amount)
            if recovered:
                aggregates[m]["recovered_count"] += 1

        metrics = []
        for m, data in aggregates.items():
            cnt = data["count"]
            rec_cnt = data["recovered_count"]
            rate = (rec_cnt / cnt * 100.0) if cnt > 0 else 0.0
            metrics.append(
                PaymentMethodMetric(
                    payment_method=m,
                    count=cnt,
                    total_revenue_at_risk=round(data["total_risk"], 2),
                    recovery_rate=round(rate, 2),
                    recovered_count=rec_cnt
                )
            )
        return metrics
