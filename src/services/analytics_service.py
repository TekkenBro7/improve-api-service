from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import base_config
from src.database.repositories.report_repository import ReportRepository
from src.database.repositories.transaction_repository import TransactionRepository
from src.database.repositories.user_repository import UserRepository


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)
        self.tx_repo = TransactionRepository(session)
        self.report_repo = ReportRepository(session)

    async def get_weekly_analysis(self) -> list[dict]:
        """
        Generate weekly analytics for a configurable number of past weeks.

        For each week, the following metrics are calculated:
            - start_date: Monday of the week
            - end_date: Sunday of the week
            - registered_users_count: total number of users registered during the week
            - deposit_distinct_users_count: number of distinct users who made at least one deposit
            - not_rollbacked_deposit_amount: total sum of deposits that were not rollbacked
            - not_rollbacked_withdraw_amount: total sum of withdrawals that were not rollbacked
            - transactions_count: total number of transactions
            - not_rollbacked_transactions_count: total number of transactions that were not rollbacked

        The method iterates backwards from the current week for a number of weeks
        defined in `base_config.amount_weeks_analyse`.

        Returns:
            list[dict]: A list of dictionaries containing weekly metrics. Each dictionary
                        corresponds to one week, with metrics as keys.

        """
        today = datetime.utcnow().date()

        current_week_start = today - timedelta(days=today.weekday())
        current_week_end = current_week_start + timedelta(days=6)
        amount_weeks = base_config.AMOUNT_WEEKS_ANALYSE

        results = []

        for _ in range(amount_weeks):
            result = {
                "start_date": current_week_start,
                "end_date": current_week_end,
                "registered_users_count": await self.user_repo.count_registered_between(
                    current_week_start, current_week_end
                ),
                "deposit_distinct_users_count": await self.report_repo.count_users_with_deposit_between(
                    dt_from=current_week_start,
                    dt_to=current_week_end,
                ),
                "not_rollbacked_deposit_amount": await self.tx_repo.get_total_amount_between(
                    dt_from=current_week_start,
                    dt_to=current_week_end,
                    deposits_only=True,
                    exclude_rollbacked=True,
                ),
                "not_rollbacked_withdraw_amount": await self.tx_repo.get_total_amount_between(
                    dt_from=current_week_start,
                    dt_to=current_week_end,
                    withdraws_only=True,
                    exclude_rollbacked=True,
                ),
                "transactions_count": await self.tx_repo.count_transactions_between(
                    current_week_start,
                    current_week_end,
                ),
                "not_rollbacked_transactions_count": await self.tx_repo.count_transactions_between(
                    current_week_start,
                    current_week_end,
                    exclude_rollbacked=True,
                ),
            }

            results.append(result)
            current_week_start -= timedelta(weeks=1)
            current_week_end -= timedelta(weeks=1)

        return results
