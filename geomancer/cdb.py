from cartodb import CartoDBAPIKey
import logging

def csv_to_sql(csv, table):
	"Return supplied CSV converted to SQL INSERT statements."
	statements = []
	header = None
	for line in csv.split('\n'):
		if not header:
			header = line.replace('\t', ',')
			continue
		name, longitude, latitude, uncertainty = line.split('\t')
		vals = "'%s',%s,%s,%s" % (name, longitude, latitude, uncertainty)
		sql = 'INSERT into %s (%s) VALUES (%s);' % (table, header, vals)
		statements.append(sql)
	return '\n'.join(statements)

def save_results(csv, user, table, api_key):	
	"Save CSV results to supplied CartoDB table and return table URL."
	logging.info(user)
	logging.info(table)
	logging.info(api_key)

	cl = CartoDBAPIKey(api_key, user)
	cl.sql(csv_to_sql(csv, table))
	return 'http://%s.cartodb.com/tables/%s' % (user, table)
