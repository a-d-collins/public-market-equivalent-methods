# coding=utf-8
import datetime

from common.model_enums import TransactionTypeEnum

from common.utils.bisect_helpers import BisectHelpers
from common.utils.transaction_utils import TransactionUtils
from common.utils.utils import get_unique_values
from common.utils.xirr_utils import XirrsUtils


class PmeUtils(object):
    """
    Utilities for calculating public market equivalents (PMEs).
    """
    bisect_helpers = None
    transaction_utils = None
    utils = None
    xirrs_utils = None

    def __init__(self, bisect_helpers=None, transaction_utils=None, xirr_utils=None):
        self.bisect_helpers = bisect_helpers or BisectHelpers()
        self.transaction_utils = transaction_utils or TransactionUtils()
        self.xirrs_utils = xirr_utils or XirrsUtils()

    def calculate_long_nickels_PME(self, benchmark_returns, investment_transactions, calculate_xirr=False, calculate_tvpi=False):
        """
        Calculate Long-Nickels PME (an IRR) for all benchmark returns. First, produce a timeseries of values for a
        "theoretical investment" in an index and then calculate an xirrs timeseries using the new theoretical investment
        series as the "returns" and the transactions from investmentGroupSet's primary investment as the transactions.

        Each theoretical investment value is determined by the previous theoretical investment value, the time weighted
        return of the benchmark, and the total value of all transactions on the date of the benchmark return.

        NOTE that the benchmark_returns list contains the benchmark returns on the dates of the primary investment's
        returns AS WELL AS the returns on the dates of the primary investment's transactions. As a result, there will
        always be a benchmark return on the date of a transaction.
        :param benchmark_returns: return series of a given benchmark, ordered by date
        :param investment_transactions: transactions of the investmentGroupSet's primary investment
        :return: benchmark returns with longNickelsPME attribute filled in for all returns

        The "balance" in this case is the value of the theoretical investment on a given date.
        """
        # Group contributions by date
        contributions_aggregated_by_date = [{
            "date": datetime.datetime.strptime(x["date"], "%Y-%m-%d"),
            "value": x["value"]
        } for x in self.transaction_utils.aggregate_transactions_by_date(investment_transactions, transaction_type_id=TransactionTypeEnum.Contribution)]

        # Group distributions by date
        distributions_aggregated_by_date = [{
            "date": datetime.datetime.strptime(x["date"], "%Y-%m-%d"),
            "value": x["value"]
        } for x in self.transaction_utils.aggregate_transactions_by_date(investment_transactions, transaction_type_id=TransactionTypeEnum.Distribution)]

        prev_value = None
        cumulative_contributions = 0.0
        cumulative_distributions = 0.0
        theoretical_investment_series = []
        for benchmark_return in benchmark_returns:
            theoretical_investment_series_item = {
                "date": benchmark_return["date"],
                "balance": None
            }

            current_date = datetime.datetime.strptime(benchmark_return["date"], "%Y-%m-%d")

            current_value = 0.0
            if prev_value:
                current_value = prev_value * (1 + benchmark_return["timeWeightedReturn"])

            # If there are contributions or distributions on the current date, add their values to current_value and
            # add to cumulative_contributions and/or cumulative_distributions.
            contribution = self.bisect_helpers.find_eq_by_key(contributions_aggregated_by_date, current_date, "date")
            distribution = self.bisect_helpers.find_eq_by_key(distributions_aggregated_by_date, current_date, "date")

            if contribution is not None:
                current_value += contribution["value"]
                cumulative_contributions += contribution["value"]

            if distribution is not None:
                current_value += distribution["value"]
                cumulative_distributions += distribution["value"]

            theoretical_investment_series_item["balance"] = current_value
            theoretical_investment_series.append(theoretical_investment_series_item)

            # calculate dpi, rvpi, and tvpi
            if calculate_tvpi and cumulative_contributions:
                benchmark_return["dpi"] = -1 * cumulative_distributions / cumulative_contributions
                benchmark_return["rvpi"] = current_value / cumulative_contributions
                benchmark_return["tvpi"] = benchmark_return["dpi"] + benchmark_return["rvpi"]
            elif calculate_tvpi:
                benchmark_return["dpi"] = 0.0
                benchmark_return["rvpi"] = 0.0
                benchmark_return["tvpi"] = benchmark_return["dpi"] + benchmark_return["rvpi"]

            prev_value = current_value

        # calculate PME (xirr)
        if calculate_xirr:
            xirrs = self.xirrs_utils.read_xirrs_timeseries(None, theoretical_investment_series, investment_transactions)

            for (i, xirr) in enumerate(xirrs):
                benchmark_returns[i]["xirr"] = xirr["xirr"]

        return benchmark_returns

    def calculate_mPME(self, benchmark_returns, investment_returns, investment_transactions, calculate_xirr=False, calculate_tvpi=False):
        """
        Like the LN-PME, the modified Public Market Equivalent (mPME) considers an hypothetical investment whose
        performance follows that of a public index/benchmark. Each contribution to the selected private investment is
        matched by an equal contribution to the index. Instead of matching the private investment's distributions,
        however, the distributions are weighted such that the same proportion is removed from the public investment as
        was removed from the private investment.
        :param benchmark_returns: return series of a given benchmark, ordered by date
        :param investment_returns: returns of the investmentGroupSet's primary investment
        :param investment_transactions: transactions of the investmentGroupSet's primary investment
        :return:
        """
        # Group contributions by date
        contributions_aggregated_by_date = [{
            "date": datetime.datetime.strptime(x["date"], "%Y-%m-%d"),
            "value": x["value"]
        } for x in self.transaction_utils.aggregate_transactions_by_date(investment_transactions, transaction_type_id=TransactionTypeEnum.Contribution)]

        # Group distributions by date
        distributions_aggregated_by_date = [{
            "date": datetime.datetime.strptime(x["date"], "%Y-%m-%d"),
            "value": x["value"]
        } for x in self.transaction_utils.aggregate_transactions_by_date(investment_transactions, transaction_type_id=TransactionTypeEnum.Distribution)]

        # Convert investment_returns dates to datetime.datetime and sort returns by date
        datetime_investment_returns = []
        for investment_return in investment_returns:
            single_return = {}
            single_return.update(investment_return)
            single_return["date"] = datetime.datetime.strptime(single_return["date"], "%Y-%m-%d")
            datetime_investment_returns.append(single_return)

        sorted_investment_returns = sorted(datetime_investment_returns, key=lambda x: x["date"])

        # For each benchmark return, compute a theoretical balance report and a weighted distribution value
        prev_theoretical_balance = None
        prev_benchmark_balance = None
        cumulative_contributions = 0.0
        cumulative_weighted_distributions = 0.0
        theoretical_balances = []
        weighted_distributions = []
        for benchmark_return in benchmark_returns:
            theoretical_balances_item = {
                "date": benchmark_return["date"],
                "balance": None
            }

            weighted_distributions_item = {
                "date": benchmark_return["date"],
                "value": None
            }

            current_date = datetime.datetime.strptime(benchmark_return["date"], "%Y-%m-%d")

            # get contribution, distribution, and most recent return for this date
            contribution = self.bisect_helpers.find_eq_by_key(contributions_aggregated_by_date, current_date, "date")
            distribution = self.bisect_helpers.find_eq_by_key(distributions_aggregated_by_date, current_date, "date")
            most_recent_return = self.bisect_helpers.find_le_by_key(sorted_investment_returns, current_date, "date")

            # Calculate Distribution Weight
            distribution_weight = 0.0
            if distribution is not None and most_recent_return is not None:
                distribution_weight = -distribution["value"] / (-distribution["value"] + most_recent_return["balance"])

            # Compute theoretical balance report and weighted distribution, using:
            # - Previous theoretical balance
            # - Previous benchmark balance and balance at date of pme measurement
            # - Contributions on that date
            # - Distribution weight
            # adjusted_balance is equivalent to the value of the theoretical investment without the removal of the distributions
            prev_theoretical_balance = prev_theoretical_balance if prev_theoretical_balance is not None else 0.0
            prev_benchmark_balance = prev_benchmark_balance if prev_benchmark_balance is not None else benchmark_return["balance"]

            adjusted_balance = prev_theoretical_balance * (benchmark_return["balance"] / prev_benchmark_balance) + \
                (contribution["value"] if contribution is not None else 0.0)

            theoretical_balance = (1 - distribution_weight) * adjusted_balance
            weighted_distribution = -1 * distribution_weight * adjusted_balance

            theoretical_balances_item["balance"] = theoretical_balance
            theoretical_balances.append(theoretical_balances_item)

            weighted_distributions_item["value"] = weighted_distribution
            weighted_distributions.append(weighted_distributions_item)

            # calculate dpi, rvpi, and tvpi
            cumulative_contributions += contribution["value"] if contribution is not None else 0.0
            cumulative_weighted_distributions += weighted_distribution

            if calculate_tvpi and cumulative_contributions:
                benchmark_return["dpi"] = -1 * cumulative_weighted_distributions / cumulative_contributions
                benchmark_return["rvpi"] = theoretical_balance / cumulative_contributions
                benchmark_return["tvpi"] = benchmark_return["dpi"] + benchmark_return["rvpi"]
            elif calculate_tvpi:
                benchmark_return["dpi"] = 0.0
                benchmark_return["rvpi"] = 0.0
                benchmark_return["tvpi"] = benchmark_return["dpi"] + benchmark_return["rvpi"]

            # Set "previous values" for next iteration of loop
            prev_theoretical_balance = theoretical_balance
            prev_benchmark_balance = benchmark_return["balance"]

        # Run xirr calculation using Theoretical Balances as "returns" and Contributions list + Weighted Distributions list as transactions
        if calculate_xirr:
            contributions_aggregated_by_date = [{
                "date": datetime.datetime.strftime(x["date"], "%Y-%m-%d"),
                "value": x["value"]
            } for x in contributions_aggregated_by_date]

            xirrs = self.xirrs_utils.read_xirrs_timeseries(None, theoretical_balances, (contributions_aggregated_by_date + weighted_distributions))

            for (i, xirr) in enumerate(xirrs):
                benchmark_returns[i]["xirr"] = xirr["xirr"]

        return benchmark_returns

    def calculate_kaplan_schoar_PME(self, benchmark_returns, investment_transactions, calculate_tvpi=False):
        """
        Calculate Kaplan Schoar (KS) PME multiple. The KS PME is sometimes justified as the LP's valuation if capital
        calls had instead been invested in the public market and distributions are reinvested into the market ("The
        Public Market Equivalent and Private Equity Performance", Sorensen & Jagannathan, 2014). In other words, the KS
        PME gives a direct indication of the performance of a selected fund/company compared to the performance of the
        selected index. A KS PME above 1 indicates that the selected fund/company performed better than an investment in
        the index. A KS PME below 1 indicates that the index would have been a better investment than the selected
        fund/company.

        KS-PME = (Discounted distributions) / (Discounted contributions)

        such that the "discount factor" for each cash flow = (index value at time of pme measurement) / (value of index at time of cash flow)
        :param benchmark_returns: return series of a given benchmark, ordered by date
        :param investment_transactions: list of transactions for the current investmentGroupSet's primary investment
        :return: benchmark_returns list with "kaplanSchoarMultiple" attribute filled in for all returns
        """
        distributions_aggregated_by_date = [{
            "date": datetime.datetime.strptime(x["date"], "%Y-%m-%d"),
            "value": x["value"]
        } for x in self.transaction_utils.aggregate_transactions_by_date(investment_transactions, transaction_type_id=TransactionTypeEnum.Distribution)]

        contributions_aggregated_by_date = [{
            "date": datetime.datetime.strptime(x["date"], "%Y-%m-%d"),
            "value": x["value"]
        } for x in self.transaction_utils.aggregate_transactions_by_date(investment_transactions, transaction_type_id=TransactionTypeEnum.Contribution)]

        cumulative_contributions = 0.0
        prev_discounted_distribution_value = None
        prev_discounted_contribution_value = None
        for benchmark_return in benchmark_returns:
            current_date = datetime.datetime.strptime(benchmark_return["date"], "%Y-%m-%d")

            # Determine total discounted distribution value
            total_discounted_distribution_value = 0.0
            if prev_discounted_distribution_value is not None:
                total_discounted_distribution_value = prev_discounted_distribution_value * (1 + benchmark_return["timeWeightedReturn"])

            distribution = self.bisect_helpers.find_eq_by_key(distributions_aggregated_by_date, current_date, "date")
            if distribution is not None:
                total_discounted_distribution_value += distribution["value"]

            # Determine total discounted contribution value
            total_discounted_contribution_value = 0.0
            if prev_discounted_contribution_value is not None:
                total_discounted_contribution_value = prev_discounted_contribution_value * (1 + benchmark_return["timeWeightedReturn"])

            contribution = self.bisect_helpers.find_eq_by_key(contributions_aggregated_by_date, current_date, "date")
            if contribution is not None:
                total_discounted_contribution_value += contribution["value"]
                cumulative_contributions += contribution["value"]

            # Calculate pme
            if total_discounted_contribution_value != 0:
                benchmark_return["kaplanSchoarMultiple"] = total_discounted_distribution_value / (-1 * total_discounted_contribution_value)
            else:
                benchmark_return["kaplanSchoarMultiple"] = 0

            # Calculate dpi, rvpi, and tvpi
            if calculate_tvpi and cumulative_contributions:
                benchmark_return["dpi"] = -1 * total_discounted_distribution_value / cumulative_contributions
                benchmark_return["rvpi"] = (total_discounted_contribution_value + total_discounted_distribution_value) / cumulative_contributions
                benchmark_return["tvpi"] = benchmark_return["dpi"] + benchmark_return["rvpi"]
            elif calculate_tvpi:
                benchmark_return["dpi"] = 0.0
                benchmark_return["rvpi"] = 0.0
                benchmark_return["tvpi"] = benchmark_return["dpi"] + benchmark_return["rvpi"]

            # Set "previous values" for next iteration
            prev_discounted_distribution_value = total_discounted_distribution_value
            prev_discounted_contribution_value = total_discounted_contribution_value

        return benchmark_returns

    def __get_benchmark_returns(self, benchmark_values, investment_returns, investment_transactions):
        """
        Given benchmark values and investment returns and transactions, calculate benchmark returns for the same set of
        dates as the returns and transactions.
        :param benchmark_values: Balances of benchmark, at whatever granularity is available (quarterly, monthly, etc).
        :param investment_returns: returns of the investmentGroupSet's primary investment
        :param investment_transactions: transactions of the investmentGroupSet's primary investment
        :return: series of benchmark returns of the form: {
            date,
            balance,
            timeWeightedReturn,
            cumulativeTimeWeightedReturn,
            kaplanSchoarMultiple,
            xirr,
            dpi,
            rvpi,
            tvpi
        }
        """
        # Catch invalid state(s)
        if len(benchmark_values) == 0:
            raise Exception("Invalid state: Benchmark values list should never be empty.")

        # 1) Ensure that benchmark values are in datetime.datetime form + sort values
        for br in benchmark_values:
            br["date"] = datetime.datetime(br["date"].year, br["date"].month, br["date"].day)

        benchmark_values = sorted(benchmark_values, key=lambda x: x["date"])

        # 2) Determine index values on dates of transactions and/or returns
        #  - TODO: If no returns, use quarter/month/etc. dates between initial transaction and current date
        index_values = []
        for date in get_unique_values([investment_returns, investment_transactions], "date"):
            date = datetime.datetime.strptime(date, "%Y-%m-%d")

            index_value = {}

            benchmark_value = self.bisect_helpers.find_le_by_key(benchmark_values, date, "date")
            if benchmark_value is not None:
                index_value.update(benchmark_value)
            else:
                index_value.update(self.bisect_helpers.find_gt_by_key(benchmark_values, date, "date"))

            index_value["date"] = date

            index_values.append(index_value)

        index_values = sorted(index_values, key=lambda x: x["date"])

        # 3) Calculate timeWeightedReturn (TWR) and cumulative TWR for each index value
        benchmark_returns = []
        prev_value = None
        cumulative_return = 1.0

        for x in index_values:
            return_ = 0.0
            if prev_value:
                return_ = (x["value"] - prev_value) / prev_value

            cumulative_return *= (return_ + 1.0)

            prev_value = x["value"]

            benchmark_returns.append({
                "date": datetime.datetime.strftime(x["date"], "%Y-%m-%d"),
                "balance": x["value"],
                "timeWeightedReturn": return_,
                "cumulativeTimeWeightedReturn": cumulative_return,
                "kaplanSchoarMultiple": None,
                "xirr": None,
                "dpi": None,
                "rvpi": None,
                "tvpi": None
            })

        return benchmark_returns
