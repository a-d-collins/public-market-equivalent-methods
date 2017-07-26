# coding=utf-8

from scipy.optimize import brenth
import datetime

from transaction_utils import TransactionUtils


class XirrsUtils(object):
    """
    Utilities for computing XIRR or XIRR timeseries.
    """
    transaction_utils = None

    def __init__(self, transaction_utils=None):
        self.transaction_utils = transaction_utils or TransactionUtils()

    def read_xirrs_timeseries(self, returns, transactions):
        """
        Given the returns and transactions for an investment, returns a timeseries of XIRR values.
        Note that if returns is None, the transactions' dates determine the data points.
        If returns is not None, the returns' dates determine the data points.
        :param returns: An investment's returns.
        :param transactions: An investment's transactions.
        :return: List of objects containing dates and XIRRs on those dates.
        """

        # Group all transactions and flip sign of transactions to give the xirr formula the proper inputs.
        transactions_aggregated_by_date = self.transaction_utils.aggregate_transactions_by_date(transactions)
        for txn in transactions_aggregated_by_date:
            txn["value"] *= -1

        # Build the XIRR timeseries
        xirrs = []
        if returns is None and len(transactions_aggregated_by_date) > 0:
            xirrs = [{
                "date": transactions_aggregated_by_date[i]["date"],
                "xirr": self.calculate_xirr(transactions_aggregated_by_date[0:i+1])
            } for i in xrange(len(transactions_aggregated_by_date))]

            return xirrs
        elif returns is not None:
            for i in xrange(len(returns)):
                filtered_transactions = [{
                    "date": x["date"],
                    "value": x["value"]
                } for x in transactions_aggregated_by_date if datetime.datetime.strptime(x["date"], "%Y-%m-%d") <= datetime.datetime.strptime(returns[i]['date'], '%Y-%m-%d')]

                returns[i]["xirr"] = self.calculate_xirr(filtered_transactions + [{
                    "date": returns[i]["date"],
                    "value": returns[i]["balance"]
                }])

            return returns
        else:
            return [x for x in xirrs if x["value"] is not None]

    def calculate_xirr(self, transactions):
        """
        Build the xirr function and run scipy's brenth() zero-finder to find the XIRR for a given investment.
        Specifically, given a list of transactions, XIRR is the solution r of:
            0 = sum([C_n/(1+r)^(t_n)]) where t_n is the number of days since time 0 and C_n is the total cash flow at
            time n. This is a generalization of the IRR formula where t_n is an integer.
        :param transactions: = [{date, value}]
        :return: the XIRR value for the given transactions.
        """

        # sort transactions by date
        transactions = sorted(transactions, key=lambda x: x["date"])

        # if all positives, return None
        # if all negatives, return -100
        # check for one positive and one negative value
        if all([x["value"] >= 0 for x in transactions]):
            return None
        elif all([x["value"] <= 0 for x in transactions]):
            return -1

        transaction_array = []

        initial_date = datetime.datetime.strptime(transactions[0]["date"], "%Y-%m-%d") \
            if type(transactions[0]["date"]) is str \
            else transactions[0]["date"]
        # for each transaction find the name
        # TODO fix the leap year math here
        for transaction in transactions:
            if type(transaction["date"]) is str:
                final_date = datetime.datetime.strptime(transaction["date"], "%Y-%m-%d")
            else:
                final_date = transaction["date"]

            if len(transactions) > 0:
                time_diff = final_date - initial_date
                transaction_array.append({
                    "value": transaction["value"] or 0.0,
                    "time_diff_days": time_diff.days,
                })

        # Note: The use of 365 for the number of days in the year matches Excel's implementation
        xirr = lambda r: reduce(lambda x,y: x + y["value"]/(1.0 + r)**(float(y["time_diff_days"])/365), transaction_array, 0.0)

        # We handle the following cases (ordered for optimization):
        # Case 1 (classic IRR) - low interest rate (-100% + epsilon) is good, high interest rate (10,000%) is bad
        # Case 2 (loan) - low interest rate (-100% + epsilon) is bad, high interest rate (10,000%) is good
        # Case 3 - check for multiple solutions if both high and low interest rates give + or both give -
        # Note that case 1 and 2 are handled by the "if" branch.
        if (xirr(-.999) > 0 and xirr(100) < 0) or (xirr(-.999) < 0 and xirr(100) > 0):
            return brenth(xirr, -.999, 100)
        else:
            # TODO handle case 3, as follows:
            # Find the local mins + maxes of this IRR function
            # Feed each pair of these + the bounds into brenth
            # Find the closest solution to the previous value

            # If there are still no solutions, return None to signify we couldn't calculate an XIRR
            return None
