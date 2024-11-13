from flask import Flask, render_template, request, session
from flask_mysqldb import MySQL
from flask import redirect, url_for
from flask import session
from datetime import timedelta
import hashlib
from json import dumps
import time
import os

app = Flask(__name__)
mysql = MySQL(app)
db_config = {
    'mysql_user': 'KapishBhalodia',
    'mysql_password': 'kapish20',
    'mysql_host': 'localhost',
    'mysql_db': 'portfoliomanagement'
}
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Set secret key securely: Use an environment variable if set, else generate a random key
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))  # Use environment variable or generate random key
app.permanent_session_lifetime = timedelta(minutes=10)  # Session lasts for 10 minutes

app.config['MYSQL_USER'] = db_config['mysql_user']
app.config['MYSQL_PASSWORD'] = db_config['mysql_password']
app.config['MYSQL_HOST'] = db_config['mysql_host']
app.config['MYSQL_DB'] = db_config['mysql_db']
# Default is tuples
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

@app.route('/', methods=['GET', 'POST'])
def index():
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        form_type = request.form['form_type']

        # Handling login form
        if form_type == 'login':
            username = request.form['username']
            password = request.form['password']
            password_hashed = hashlib.sha224(password.encode()).hexdigest()
            
            cur.execute("SELECT username, user_password FROM user_profile WHERE username = %s", (username,))
            user = cur.fetchone()
            
            # Verify credentials
            if user and user['user_password'] == password_hashed:
                session['user'] = username
                return redirect(url_for('watchlist'))
            else:
                return render_template('alert2.html', message="Incorrect username or password.")

        # Handling registration form
        elif form_type == 'register':
            username = request.form['username']
            password = request.form['password']
            password_hashed = hashlib.sha224(password.encode()).hexdigest()

            # Check if the username already exists
            cur.execute("SELECT username FROM user_profile WHERE username = %s", (username,))
            existing_user = cur.fetchone()
            
            if existing_user:
                return render_template('alert2.html', message="Username already exists.")
            
            try:
                # Attempt to insert new user
                cur.execute("INSERT INTO user_profile (username, user_password) VALUES (%s, %s)", (username, password_hashed))
                mysql.connection.commit()  # Commit the transaction
                print("User registered successfully")
                return render_template('alert2.html', message="Registration successful! Please log in.")
            except Exception as e:
                mysql.connection.rollback()  # Roll back in case of an error
                print(f"Error during registration: {e}")
                return render_template('alert2.html', message="Registration failed. Please try again.")

    return render_template('index.html')

@app.route('/portfolio.html')
def portfolio():

    # Check if we have logged in users
    if "user" not in session:
        return render_template('alert1.html')

    # Query for holdings

    cur = mysql.connection.cursor()
    user = [session['user']]
    cur.callproc('portfolio', user)
    query_holdings = '''
SELECT
    hv.symbol,
    hv.quantity,
    cp.LTP,
    ROUND(hv.quantity * cp.LTP, 2) AS current_value,
    ROUND(hv.quantity * hv.avg_rate, 2) AS purchase_value,
    CASE
        WHEN hv.quantity = 0 AND hv.sell_rate IS NOT NULL THEN
            ROUND((hv.sell_rate - hv.avg_rate) * (SELECT SUM(quantity) FROM holdings_view WHERE username = hv.username AND symbol = hv.symbol), 2)
        ELSE
            ROUND((hv.quantity * cp.LTP) - (hv.quantity * hv.avg_rate), 2)
    END AS profit_loss,
    hv.avg_rate AS buy_rate,
    hv.sell_rate AS sell_rate
FROM
    holdings_view hv
INNER JOIN company_price cp ON hv.symbol = cp.symbol
WHERE
    hv.username = %s
'''

    cur.execute(query_holdings, user)
    holdings = cur.fetchall()
    # Query for watchlist
    query_watchlist = '''select symbol, LTP, PC, round((LTP-PC), 2) AS CH, round(((LTP-PC)/PC)*100, 2) AS CH_percent from watchlist
natural join company_price
where username = %s
order by (symbol)
'''
    cur.execute(query_watchlist, user)
    watchlist = cur.fetchall()

    # Query for stock suggestion
    query_suggestions = '''select symbol, EPS, ROE, book_value, rsi, adx, pe_ratio, macd from company_price
natural join fundamental_averaged
natural join technical_signals
natural join company_profile 
where 
EPS>25 and roe>13 and 
book_value > 100 and
rsi>50 and adx >23 and
pe_ratio < 35 and
macd = 'bull'
order by symbol;
'''
    cur.execute(query_suggestions)
    suggestions = cur.fetchall()

    # Query on EPS
    query_eps = '''select symbol, ltp, eps from fundamental_averaged
where eps > 30
order by eps;'''
    cur.execute(query_eps)
    eps = cur.fetchall()

    # Query on PE Ratio
    query_pe = '''select symbol, ltp, pe_ratio from fundamental_averaged
where pe_ratio <30;'''
    cur.execute(query_pe)
    pe = cur.fetchall()

    # Query on technical signals
    query_technical = '''select * from technical_signals
where ADX > 23 and rsi>50 and rsi<70 and MACD = 'bull';'''
    cur.execute(query_technical)
    technical = cur.fetchall()

    # Query for pie chart
    query_sectors = '''SELECT C.sector, SUM(P.quantity * B.LTP) AS current_value 
FROM portfolio_table P
INNER JOIN company_price B ON P.symbol = B.symbol
INNER JOIN company_profile C ON B.symbol = C.symbol
WHERE username = %s
GROUP BY C.sector;
'''
    cur.execute(query_sectors, user)
    sectors_total = cur.fetchall()
    # Convert list to json type having percentage and label keys
    piechart_dict = toPercentage(sectors_total)
    piechart_dict[0]['type'] = 'pie'
    piechart_dict[0]['hole'] = 0.4

    return render_template('portfolio.html', holdings=holdings, user=user[0], suggestions=suggestions, eps=eps, pe=pe, technical=technical, watchlist=watchlist, piechart=piechart_dict) 


def toPercentage(sectors_total):
    json_format = {}
    total = 0

    for row in sectors_total:
        total += row[1]

    json_format['values'] = [round((row[1]/total)*100, 2) for row in sectors_total]
    json_format['labels'] = [row[0] for row in sectors_total]
    return [json_format]
    
def list_to_json(listToConvert):
    json_format = {}
    temp_dict = {}
    val_per = []
    for value in listToConvert:
        temp_dict[value] = listToConvert.count(value)

    values = [val for val in temp_dict.values()]
    for i in range(len(values)):
        per = ((values[i]/sum(values))*100)
        val_per.append(round(per, 2))
    keys = [k for k in temp_dict.keys()]
    json_format['values'] = val_per
    json_format['labels'] = keys
    return [json_format]

from flask import session

@app.route('/add_transaction.html', methods=['GET', 'POST'])
def add_transaction():
    cur = mysql.connection.cursor()

    # Fetching all company symbols from the database
    query = "SELECT symbol FROM company_price"
    cur.execute(query)
    companies = cur.fetchall()

    if request.method == 'POST':
        # Retrieve form data
        symbol = request.form['symbol']
        transaction_date = request.form['transaction_date']
        transaction_type = request.form['transaction_type']  # Get the transaction type (buy/sell)
        quantity = request.form['quantity']
        rate = request.form['rate']
        username = session['user']

        # Insert the transaction into the database
        insert_query = """
            INSERT INTO transaction_history (symbol, transaction_date, quantity, rate, transaction_type, username)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (symbol, transaction_date, quantity, rate, transaction_type, username))
        mysql.connection.commit()

        return redirect('/portfolio.html')  # Redirect after submitting

    return render_template('add_transaction.html', companies=companies)

@app.route('/add_watchlist.html', methods=['GET', 'POST'])
def add_watchlist():
    # Query for companies (for drop down menu) excluding those which are already in watchlist
    cur = mysql.connection.cursor()
    query_companies = '''SELECT symbol from company_profile
                         WHERE symbol NOT IN
                         (SELECT symbol from watchlist
                          WHERE username = %s);'''
    user = [session['user']]
    cur.execute(query_companies, user)
    companies = cur.fetchall()

    # Query for the current watchlist
    query_watchlist = '''SELECT symbol FROM watchlist WHERE username = %s'''
    cur.execute(query_watchlist, user)
    watchlist = cur.fetchall()

    if request.method == 'POST':
        # Check if it's for adding or deleting
        if 'symbol' in request.form:
            # Adding to watchlist
            symbol = request.form['symbol']

            # Check if the symbol exists in company_profile
            cur.execute('SELECT symbol FROM company_profile WHERE symbol = %s', (symbol,))
            company_exists = cur.fetchone()

            if company_exists:  # If the symbol exists in company_profile
                query = '''INSERT INTO watchlist(username, symbol) VALUES (%s, %s)'''
                values = [session['user'], symbol]
                cur.execute(query, values)
                mysql.connection.commit()
                return redirect(url_for('add_watchlist'))  # Redirect to the same page to refresh the list
            else:
                return render_template('alert.html', message="The selected symbol does not exist.")  # Show an alert if the symbol doesn't exist

        if 'delete_symbol' in request.form:
            # Deleting from watchlist
            delete_symbol = request.form['delete_symbol']
            delete_query = '''DELETE FROM watchlist WHERE username = %s AND symbol = %s'''
            cur.execute(delete_query, (session['user'], delete_symbol))
            mysql.connection.commit()
            return redirect(url_for('add_watchlist'))  # Redirect to the same page to refresh the list

    return render_template('add_watchlist.html', companies=companies, watchlist=watchlist)


@app.route('/delete_from_watchlist', methods=['POST'])
def delete_from_watchlist():
    symbol = request.form['symbol']
    cur = mysql.connection.cursor()
    # Delete from watchlist
    delete_query = '''DELETE FROM watchlist WHERE username = %s AND symbol = %s'''
    cur.execute(delete_query, (session['user'], symbol))
    mysql.connection.commit()

    # Redirect back to the watchlist page
    return redirect(url_for('watchlist'))


@app.route('/stockprice.html')
def current_price(company='all'):
    cur = mysql.connection.cursor()
    if company == 'all':
        query = '''SELECT symbol, LTP, PC, round((LTP-PC), 2) as CH, round(((LTP-PC)/PC)*100, 2) AS CH_percent FROM company_price
        order by symbol;'''
        cur.execute(query)
    else:
        company = [company]
        query = '''SELECT symbol, LTP, PC, round((LTP-PC), 2) as CH, round(((LTP-PC)/PC)*100, 2) AS CH_percent FROM company_price
        where symbol = %s;'''
        cur.execute(query, company)

    rv = cur.fetchall()
    print(rv)  # Add a print statement here to see the fetched data in the console
    return render_template('stockprice.html', values=rv)

@app.route('/fundamental.html', methods=['GET'])
def fundamental_report(company='all'):
    cur = mysql.connection.cursor()
    if company == 'all':
        query = '''select * from  fundamental_averaged;'''
        cur.execute(query)
    else:
        company = [company]
        query = '''select F.symbol, report_as_of, LTP, eps, roe, book_value, round(LTP/eps, 2) as pe_ratio
from fundamental_report F
inner join company_price C
on F.symbol = C.symbol
where F.symbol = %s'''
        cur.execute(query, company)
    rv = cur.fetchall()
    return render_template('fundamental.html', values=rv)


@app.route('/technical.html')
def technical_analysis(company='all'):
    cur = mysql.connection.cursor()
    if company == 'all':
        query = '''select A.symbol, sector, LTP, volume, RSI, ADX, MACD from technical_signals A 
left join company_profile B
on A.symbol = B.symbol
order by (A.symbol)'''
        cur.execute(query)
    else:
        company = [company]
        query = '''SELECT * FROM technical_signals where company = %s'''
        cur.execute(query, company)
    rv = cur.fetchall()
    return render_template('technical.html', values=rv)


@app.route('/companyprofile.html')
def company_profile(company='all'):
    cur = mysql.connection.cursor()
    if company == 'all':
        query = '''select * from company_profile
order by(symbol);
'''
        cur.execute(query)
    else:
        company = [company]
        query = '''select * from company_profile where company = %s'''
        cur.execute(query, company)
    rv = cur.fetchall()
    return render_template('companyprofile.html', values=rv)


@app.route('/dividend.html')
def dividend_history(company='all'):
    cur = mysql.connection.cursor()
    if company == 'all':
        query = '''select * from dividend_history
order by(symbol);
'''
        cur.execute(query)
    else:
        company = [company]
        query = '''select * from dividend_history where company = %s'''
        cur.execute(query, company)
    rv = cur.fetchall()
    return render_template('dividend.html', values=rv)


@app.route('/watchlist.html')
def watchlist():
    if 'user' not in session:
        return render_template('alert1.html')
    cur = mysql.connection.cursor()
    query_watchlist = '''select symbol, LTP, PC, round((LTP-PC), 2) AS CH, round(((LTP-PC)/PC)*100, 2) AS CH_percent from watchlist
natural join company_price
where username = %s
order by (symbol);
'''
    cur.execute(query_watchlist, [session['user']])
    watchlist = cur.fetchall()

    return render_template('watchlist.html', user=session['user'], watchlist=watchlist)

@app.route('/holdings.html')
def holdings():
    if "user" not in session:
        return render_template('alert1.html')
    
    cur = mysql.connection.cursor()
    
    # Query to calculate P&L by joining holdings_view and company_price
    query_holdings = '''
SELECT
    hv.symbol,
    hv.quantity,
    cp.LTP,
    ROUND(hv.quantity * cp.LTP, 2) AS current_value,
    ROUND(hv.quantity * hv.avg_rate, 2) AS purchase_value,
    CASE
        WHEN hv.quantity = 0 AND hv.sell_rate IS NOT NULL THEN
            ROUND((hv.sell_rate - hv.avg_rate) * (SELECT SUM(quantity) FROM holdings_view WHERE username = hv.username AND symbol = hv.symbol), 2)
        ELSE
            ROUND((hv.quantity * cp.LTP) - (hv.quantity * hv.avg_rate), 2)
    END AS profit_loss,
    hv.avg_rate AS buy_rate,
    hv.sell_rate AS sell_rate
FROM
    holdings_view hv
INNER JOIN company_price cp ON hv.symbol = cp.symbol
WHERE
    hv.username = %s
'''
    
    cur.execute(query_holdings, [session['user']])
    holdings = cur.fetchall()

    return render_template('holdings.html', user=session['user'], holdings=holdings)

@app.route('/news.html')
def news(company='all'):
    cur = mysql.connection.cursor()
    if company == 'all':
        query = '''select date_of_news, title, related_company, C.sector, group_concat(sources) as sources 
from news N
inner join company_profile C
on N.related_company = C.symbol
group by(title);
'''
        cur.execute(query)
    else:
        company = [company]
        query = '''select date_of_news, title, related_company, related_sector, sources from news where related_company = %s'''
        cur.execute(query, company)
    rv = cur.fetchall()
    return render_template('news.html', values=rv)


if __name__ == '__main__':
    app.run(debug=True)
