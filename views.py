#app.py 
from flask import Flask, render_template, render_template, flash, redirect, request, g
from flask_wtf import Form
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import json
from urllib.request import urlopen
from operator import itemgetter
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess'

class AddressForm(Form):
    address = StringField('address', validators=[DataRequired()])

class FilterForm(Form):
    filt = StringField('filt', validators = [DataRequired()])

class BillForm(Form):
    bill_id = StringField('bill_id', validators = [DataRequired()])
def json_converter(url):
    http = urlopen(url)
    data = http.read().decode('utf-8')
    return json.loads(data)

state = ''
states = ['al', 'ak', 'az', 'ar','ca', 'co', 'ct', 'de','fl', 'ga', 'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md', 'ma', 'mi', 'mn', 'ms', 'mo', 'mt','ne', 'nv','nh', 'nj','nm','ny','nc','nd','oh','ok','or','pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi', 'wy']
assembly = [state for state in states if state == 'ca' or state == 'nj' or state == 'nv' or state == 'ny' or state == 'wi']
delegates = [state for state in states if state == 'md' or state == 'va' or state == 'wv']
legislature = ['ne']
n = 14
last_updated_datetime = datetime.now() - timedelta(days = n)
last_updated = last_updated_datetime.date()

@app.route('/', methods = ['GET', 'POST'])
@app.route('/index', methods = ['GET','POST'])
def index():
    form = AddressForm()
    address = None
    if form.validate_on_submit():
        flash('Your Address:"%s"' % (form.address.data))
        address = form.address.data
        return redirect('/reps')
    return render_template('index.html', title = 'Home', form = form)

@app.route('/reps', methods = ['GET','POST'])
def reps():
    address = request.form['address']
    query = address.replace(' ', '+')       
    location_url = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + query + '&key=AIzaSyDBRi3sLY-UewJ3WjFwhr6etMg9UmNtbbE'
    loc =json_converter(location_url)
    lat_long = (loc["results"][0]['geometry']['location']['lat'], loc["results"][0]["geometry"]["location"]['lng'])

    fed_url = "https://congress.api.sunlightfoundation.com" + "/legislators/locate?latitude=" + str(lat_long[0]) + "&longitude=" + str(lat_long[1])
    fed_json = json_converter(fed_url)
    cong = sorted([rep for rep in fed_json['results']], key = itemgetter('title'))

    state_url = "https://openstates.org/api/v1/legislators/geo/?lat=" + str(lat_long[0]) + "&long=" + str(lat_long[1])
    state_json = json_converter(state_url)
    state_leg = [rep for rep in state_json]
    global state
    state = state_leg[0]['state']
    for l in state_leg:
        if l['chamber'] == 'upper' or l['state'] == 'ne':
            l['chamber'] = 'Senate'
        elif l['state'] in assembly:
            l['chamber'] = 'Assembly'
        elif l['state'] in delegates:
            l['chamber'] = 'House of Delegates'
        else: 
            l['chamber'] = 'House of Representatives'
    return render_template('reps.html', title = 'Reps', congress = cong, state_leg = state_leg)

@app.route('/congbills', methods = ['GET', 'POST'])
def congbills():
    cong_url = 'https://congress.api.sunlightfoundation.com' + '/bills?history.active=true&order=last_action_at'
    bills_json = json_converter(cong_url)
    cong_bills = [bill for bill in bills_json['results']]
    
    form_1 = FilterForm()
    query = None

    form = BillForm()
    bill_id = None

    if form_1.validate_on_submit():
        query = form_1.filt.data
        filtered_bills = [bill for bill in cong_bills if query in bill['official_title']]
        return render_template('congbills.html', title = 'Congress Bills', bills = filtered_bills, form_1 = form_1, form = form)

    form = BillForm()
    bill_id = None
    if form.validate_on_submit():
        bill_id = form.bill_id.data
        return redirect('/fedbilldetail')

    return render_template('congbills.html', title = 'Congress Bills', bills = cong_bills, form_1 = form_1, form = form)

@app.route('/statebills', methods = ['GET', 'POST'])
def statebills():
    state_leg_url = 'http://openstates.org/api/v1/bills/?state=' + state + '&updated_since=' + str(last_updated) + '&type=bill'
    state_bills = json_converter(state_leg_url)
    
    form_1 = FilterForm()
    query = None
    form = BillForm()
    bill_id = None

    if form_1.validate_on_submit():
        query = form_1.filt.data
        filtered_bills = [bill for bill in state_bills if query in bill['title']]
        return render_template('statebills.html', title = 'State Bills', bills = filtered_bills, form_1 = form_1, form = form)
    
    if form.validate_on_submit():
        bill_id = form.bill_id.data
        return redirect('/statebilldetail')
    
    return render_template('statebills.html', title = 'State Bills', bills = state_bills, form_1 = form_1, form = form)

@app.route('/fedbilldetail', methods = ['GET', 'POST'])
def fedbilldetail():
    bill_id = request.form['bill_id']
    bill_url = 'https://congress.api.sunlightfoundation.com' + '/bills?history.active=true&order=last_action_at&bill_id=' + bill_id + '&fields=summary,official_title,short_title,popular_title,history,urls'
    bill_detail = json_converter(bill_url)
    title = ""
    if bill_detail['results'][0]['short_title']:
        title = bill_detail['results'][0]['short_title']
    elif bill_detail['results'][0]['popular_title']:
        title = bill_detail['results'][0]['popular_title']
    else:
        title = bill_detail['results'][0]['official_title']
    return render_template('fedbilldetail.html', title = 'Federal Bill Detail', b = bill_detail['results'][0], bill_title = title)


@app.route('/statebilldetail', methods = ['GET', 'POST'])
def statebilldetail():
    bill_id = request.form['bill_id']
    bill_url = 'http://openstates.org/api/v1/bills/'+bill_id
    bill_detail = json_converter(bill_url)
    return render_template('statebilldetail.html', title = 'State Bill Detail', b = bill_detail)

if __name__ == "__main__":
    app.run(debug=True)