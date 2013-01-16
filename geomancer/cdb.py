from cartodb import CartoDBAPIKey

def csv_to_sql(csv, table):
	"Return supplied CSV converted to SQL INSERT statements."
	statements = []
	header = None
	for line in csv.split('\n'):
		if not header:
			header = line
			continue
		line = ','.join(["'%s'" % x for x in line.split(',')])
		sql = 'INSERT into %s (%s) VALUES (%s);' % (table, header, line)
		statements.append(sql)
	return '\n'.join(statements)

def save_results(csv, user, api_key, table):	
	"Save CSV results to supplied CartoDB table and return table URL."
	cl = CartoDBAPIKey(api_key, user)
	cl.sql(csv_to_sql(csv, table))
	return 'http://%s.cartodb.com/tables/%s' % (user, table)
