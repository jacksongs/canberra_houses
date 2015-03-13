# This scraper collects all the houses that have ever been listed on allhomes (Starting from when it runs).
# The thinking is that this record of houses should top out at the number of dwellings in canberra.
# It also stores at any time the last listing for each house, as well as any changes that have been recorded.
# It is designed to be run once per day, and for another system to consumer and aggregate the data.

import scraperwiki
import requests
from bs4 import BeautifulSoup
import bs4
import datetime
import dateutil.parser

suburbs = requests.get("http://www.allhomes.com.au/ah/act/sale-residential/canberra/1039110")

soup = BeautifulSoup(suburbs.content)
dds = soup.find_all("dd")

subs = []
for dd in dds:
	subs.append({"Name":dd.a.text,"Link":dd.a.get('href')})
	
scraperwiki.sqlite.save(unique_keys=["Link"],data=subs,table_name='suburbs')

try:
    scraperwiki.sqlite.execute("""
        create table houses
        ( 
        id INTEGER PRIMARY KEY AUTOINCREMENT,	
        Link,
        Suburb,
        Active
        )
    """)
except:
	pass

try:
    scraperwiki.sqlite.execute("""
    	create table listings
        ( 
        id INTEGER PRIMARY KEY AUTOINCREMENT,	
        Link,
        Updated
        )
    """)
except:
	pass


for link in scraperwiki.sql.select("* from suburbs"):

	houses = [] # this is to hold all the data on the houses in each suburb for saving to the database
	
	page = requests.get("http://allhomes.com.au/"+link["Link"])
	soup = BeautifulSoup(page.content)
	trs = soup.find_all("tr")

	# first let's collect all our listings of houses in the suburb

	oldhouses = scraperwiki.sql.select("* from houses where Suburb=?",[link["Name"]])

	# now we will go through each house currently listed on allhomes and add it to our houses list

	for no,tr in enumerate(trs):
		if no == 0:
			pass
		elif tr.get("class") == ['primary_colour']:
			pass
		else:
			# so now we look at each of the houses...

			# first up, the house info

			house = {}

			# first off, the image link

			try:
				thumb = tr.td.div.a.img.get("src")
				house["Image"] = thumb.replace("_ps.jpg",".jpg")
			except Exception as e:
				print e,link["Link"],'Image did not work'


			# now, the info the icons - this is all house related

			try:
				icons = tr.td.next_sibling.next_sibling.div.div.next_sibling.next_sibling.next_sibling.next_sibling
				for i in icons.contents:
					if isinstance(i, bs4.element.NavigableString) == False:
						if i.get("class") == ['otherIcons']:
							for w in i.contents:
								if isinstance(w, bs4.element.NavigableString) == False:
									house[w.img.get("title")]=w.text.strip()
			except Exception as e:
				print e,link["Link"],'Icons did not work'

			# And this is the more generic stuff

			try:
				house["Type"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
			except Exception as e:
				print e,link["Link"],'The property type did not work'
			try:
				house["EER"] = float(tr.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text.strip())
			except Exception as e:
				print e,link["Link"],'The EER did not work'
								
			try:
				house["Address 1"]=tr.td.next_sibling.next_sibling.div.div.a.text.split(",")[0].strip()
				house["Suburb"]=link["Name"]
				house["Link"]=tr.td.next_sibling.next_sibling.div.div.a.get("href")
				house["Added"] = datetime.datetime.now()
				house["Active"] = True
			except Exception as e:
				print e,link["Link"],'Something in the main box did not work'

			# now let's add it to the list of houses for our test to see if it's no longer active a bit later
			# but let's only add it if it's a real address (and not a stupid project marketing piece of crap)
			# we only need to do this for houses because if we later try to match a listing with a non-listed house, it will not be saved
			intcatch = []
			for c in house["Address 1"]:
				try:
					int(c)
					intcatch.append(c)
				except:
					pass
			if incatch == []:
				pass
			else:
				houses.append(house)

	# so now we have the oldlistings and the new listings

	# let's first ensure houses that are now longer listed are deactivated and saved

	for o in oldhouses: # for each of the previous entries

		catch = [] # This is our catch to check if one of the new houses is the same as one of the old houses

		for ho in houses:
			if o['Address 1'] == ho['Address 1']:
				if o['Suburb'] == ho['Suburb']:
					catch.append(True)

		# we make sure we save these as otherwise they will be lost forever
		if len(catch) == 0:
			o['Active'] == False
			scraperwiki.sqlite.save(unique_keys=['Address 1','Suburb'],data=o,table_name='houses')

	# now let's save the houses listed
	for hou in houses:
		scraperwiki.sqlite.save(unique_keys=['Address 1','Suburb'],data=hou,table_name='houses')


	# alright now it's listing time!
	for no,tr in enumerate(trs):
		if no == 0:
			pass
		elif tr.get("class") == ['primary_colour']:
			pass
		else:
			try:
				# This is all about the listing
				try:
					listing = {}
					listing["Suburb"] = link["Name"]
					listing["Link"]=tr.td.next_sibling.next_sibling.div.div.a.get("href")
					listing["Sold"] = tr.find("span",class_="badge-sold")!=None
					listing["New"] = tr.find("span",class_="badge-new")!=None
					listing["New price"] = tr.find("span",class_="badge-new-price")!=None
					listing["Updated"] = datetime.datetime.now()
					listing["Auction"] = 'Auction' in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					if listing["Auction"] == True:
						if " " in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip():
							date = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().split(" ")[1]
							listing["Auction date"] = dateutil.parser.parse(date)
					listing["Under offer"] = "Under offer" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					listing["Negotiation"] = "(by negotiation)" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip() or "By Negotiation" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					listing["Range"] = "-" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					if listing["Range"] == True:
						listing["Range low"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().split("-")[0].strip()
						listing["Range high"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().split("-")[1].strip()
					listing["Upwards of"] = u"+" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					if listing["Upwards of"] == True:
						listing["Price"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().replace("+","")
					if listing["Auction"] == False:
						if listing["Under offer"] == False:
							if listing["Negotiation"] == False:
								if listing["Range"] == False:
									if listing["Upwards of"] == False:
										listing["Price"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
				except Exception as e:
					print e,link["Link"],'Something went wrong with the listing for',tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()

				# now let's get the most recent listing
				lastlisting = scraperwiki.sql.select("* from listings where Link=? and Suburb=? order by 'Updated' desc limit 1",(listing["Link"],listing["Name"]))

				snatch = []
				# first let's save the listing if it is a new house
				if lastlisting == []:
					scraperwiki.sqlite.save(unique_keys=["Link"],data=listing,table_name='listings')
					scraperwiki.sqlite.save(unique_keys=[],data={"Updated":datetime.datetime.now(),"Change":"New Listing","Old value":None,"New value":None,"Link":listing["Link"]},table_name='changes') 

				# or if there are records listed, let's see if they have changed
				else:

					for l in listing.keys():
						if l == 'Updated':
							pass
						elif l == 'Auction date':
							if listing[l] != dateutil.parser.parse(lastlisting[0][l]):
								snatch.append(l)
								scraperwiki.sqlite.save(unique_keys=[],data={"Updated":datetime.datetime.now(),"Change":"Auction date","Old value":dateutil.parser.parse(lastlisting[0][l]),"New value":listing[l],"Link":listing["Link"]},table_name='changes') 
						elif listing[l] == True:
							if 1 != lastlisting[0][l]:
								snatch.append(l)
								scraperwiki.sqlite.save(unique_keys=[],data={"Updated":datetime.datetime.now(),"Change":l,"Old value":True,"New value":False,"Link":listing["Link"]},table_name='changes') 
						elif listing[l] == False:
							if 0 != lastlisting[0][l]:
								snatch.append(l)
								scraperwiki.sqlite.save(unique_keys=[],data={"Updated":datetime.datetime.now(),"Change":l,"Old value":False,"New value":True,"Link":listing["Link"]},table_name='changes') 
						elif listing[l] != lastlisting[0][l]:
							snatch.append(l)
							scraperwiki.sqlite.save(unique_keys=[],data={"Updated":datetime.datetime.now(),"Change":l,"Old value":lastlisting[0][l],"New value":listing[l],"Link":listing["Link"]},table_name='changes') 

				# if they have changed, let's save the latest listing
				if len(snatch)>0:
					scraperwiki.sqlite.save(unique_keys=["Link"],data=listing,table_name='listings')

				# and if they haven't changed, let's do nothing
				else:
					pass

			except Exception as e:
				print e,link["Link"],'Something went wrong saving the listing'





			
