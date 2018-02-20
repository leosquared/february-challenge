from sqlalchemy import create_engine
import yaml
import pandas as pd
import logging

## logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_table(pandas_df, db_con, table_name):
	db_con.execute('DROP TABLE IF EXISTS {};'.format(table_name))
	pandas_df.to_sql(table_name, db_con, index=False)
	logger.info('Table {} created.'.format(table_name))
	return True

def establish_connection():
	with open('local_creds.yml', 'rb') as yml_file:
		credentials = yaml.safe_load(yml_file)['Postgres']
	engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(
																															credentials['username'],
																															credentials['password'],
																															credentials['host'],
																															credentials['port'],
																															credentials['database']
																															)
						)
	return engine

if __name__ == '__main__':
	
	## database connection
	db_con = establish_connection()

	## extract and load
	customers_file = pd.read_csv('data/customers.csv', parse_dates=['signup_date'])
	create_table(customers_file, db_con, 'customers')
	transactions_file = pd.read_csv('data/transactions.csv', parse_dates=['date'])
	create_table(transactions_file, db_con, 'transactions')

	## data transformation and aggregation
	sql_statement = """
		-- Filling in purchases summary based on the transactions table
		UPDATE customers c
		SET (number_of_purchases, value_of_purchases) = (agg1, agg2)

		FROM (
		    SELECT user_id, COUNT(value) AS agg1, SUM(value) AS agg2
			FROM transactions t
			GROUP BY user_id
		) ta
		WHERE c.id = ta.user_id
		;

		-- preparing table for further user aggregation and analytics on points and point redemptions
		DROP TABLE IF EXISTS transactions_derived;
		CREATE TABLE transactions_derived
		AS (
			SELECT *
			, SUM(point_differential) OVER(PARTITION BY user_id ORDER BY date ASC) AS standard_points
			, (point_differential - (value / 100 * 10)) / 5050 * -1 AS number_of_redemptions
			, ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY date ASC) AS transaction_order
			, ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY date DESC) AS transaction_recency
			FROM transactions
		)
		;

		-- final aggregations
		UPDATE customers c
		SET total_standard_points = latest_standard_points
		FROM (
			SELECT user_id, standard_points AS latest_standard_points
			FROM transactions_derived
			WHERE transaction_recency = 1
		) td
		WHERE c.id = td.user_id
		;

		UPDATE customers c
		SET total_points_redeemed = points_redeemed
		FROM (
			SELECT user_id, sum(number_of_redemptions) * 5000 AS points_redeemed
			FROM transactions_derived 
			GROUP BY user_id
		) td 
		WHERE c.id = td.user_id
		;

		COMMIT;
		"""
	db_con.execute(sql_statement)
	logger.info('Aggregation finished.')

