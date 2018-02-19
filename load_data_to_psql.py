from sqlalchemy import create_engine
import yaml
import pandas as pd

def create_table(pandas_df, db_con, table_name):
	db_con.execute('DROP TABLE IF EXISTS {};'.format(table_name))
	pandas_df.to_sql(table_name, db_con, index=False)
	print('Table {} created.\n'.format(table_name))
	return True


if __name__ == '__main__':
	## database connection
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

	customers_file = pd.read_csv('data/customers.csv', parse_dates=['signup_date'])
	create_table(customers_file, engine, 'customers')
	transactions_file = pd.read_csv('data/transactions.csv', parse_dates=['date'])
	create_table(transactions_file, engine, 'transactions')

