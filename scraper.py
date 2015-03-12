# This is a template for a Python scraper on Morph (https://morph.io)
# including some code snippets below that you should find helpful

#import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries. You can use whatever libraries are installed
# on Morph for Python (https://github.com/openaustralia/morph-docker-python/blob/master/pip_requirements.txt) and all that matters
# is that your final data is written to an Sqlite database called data.sqlite in the current working directory which
# has at least a table called data.

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

	# first we are going to get at all the houses that are recorded on the suburb page and compare them with all the houses that are marked as 'current in our database'

	oldhouses = scraperwiki.sql.select("* from houses where Active=1 and Suburb=?",[link["Name"]])

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
				house["Address 1"]=tr.td.next_sibling.next_sibling.div.div.a.text.split(",")[0]
				house["Suburb"]=link["Name"]
				house["Link"]=tr.td.next_sibling.next_sibling.div.div.a.get("href")
				house["Added"] = datetime.datetime.now()
				house["Active"] = True
			except Exception as e:
				print e,link["Link"],'Something in the main box did not work'

			# now let's add it to the list of houses for our test to see if it's no longer active a bit later
			houses.append(house)

	# now for each house we need to check if we should save it (ie if it's a new house)
	for hou in houses:

		latch = []
		
		for o in oldhouses:
			if o['Link'] == hou['Link']:
				latch.append(True)

		if len(latch) == 0: # ie: it's not in the old houses
			scraperwiki.sqlite.save(unique_keys=['Link'],data=hou,table_name='houses')

	# now we do the opposite -  check whether there are any houses that have dropped off the list

	for o in oldhouses: # for each of the previous entries

		catch = [] # This is our catch to check if one of the new houses is the same as one of the old houses

		for ho in houses:
			if o['Link'] == ho['Link']:
				catch.append(True)

		if len(catch) == 0:
			statement = "update houses set Active=0 where Link=?"
			scraperwiki.sqlite.execute(statement,o['Link'])


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
				lastlisting = scraperwiki.sql.select("* from listings where Link=? order by 'Updated' desc limit 1",[listing["Link"]])

				# let's see if they have changed
				snatch = []
				if lastlisting == []:
					scraperwiki.sqlite.save(unique_keys=[],data=listing,table_name='listings') # first we save it if there's no records listed
				else:
					for l in listing.keys():
						if l == 'Updated':
							pass
						elif l == 'Auction date':
							if listing[l] != dateutil.parser.parse(lastlisting[0][l]):
								snatch.append(l)
						elif listing[l] == True:
							if 1 != lastlisting[0][l]:
								snatch.append(l)
						elif listing[l] == False:
							if 0 != lastlisting[0][l]:
								snatch.append(l)
						elif listing[l] != lastlisting[0][l]:
							snatch.append(l)

				if len(snatch)>0:
					scraperwiki.sqlite.save(unique_keys=[],data=listing,table_name='listings')

			except Exception as e:
				print e,link["Link"],'Something went wrong saving the listing'





			
