# coding=utf-8
import datetime


class TransactionUtils(object):
    def __init__(self):
        pass

    def aggregate_transactions_by_date(self, transactions, transaction_type_id=None):
        """
        Group all transactions by date - gives at most one cash flow per date as desired.
        :param transactions: list of transactions of at least the form {
            date (string),
            value (float),
            transaction_type_id (int)
        }
        :param transaction_type_id: type of transaction to sum up
        :return: ordered list of transactions of form { date, value }
        """
        # catch invalid state(s)
        if transaction_type_id and len(transactions) > 0 and "transactionTypeId" not in transactions[0]:
            raise Exception("Invalid state: transactions must have transactionTypeId")

        if transaction_type_id:
            transactions = [x for x in transactions if x["transactionTypeId"] == transaction_type_id]

        transactions_date_sets = set([x["date"] for x in transactions])
        grouped_transactions = [[{
            "date": txn["date"],
            "value": txn["value"]
        } for txn in transactions if txn["date"] == transaction_date] for transaction_date in transactions_date_sets]
        summed_transactions = [{
            "date": group[0]["date"],
            "value": sum([(txn["value"] or 0.0) for txn in group])
        } if len(group) > 0 else None for group in grouped_transactions]

        return sorted(summed_transactions, key=lambda x: datetime.datetime.strptime(x["date"], "%Y-%m-%d"))