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
        create table data
        ( 
        Link
        )
    """)
except:
    pass

for link in scraperwiki.sql.select("* from suburbs")[4:5]:
	page = requests.get("http://allhomes.com.au/"+link["Link"])
	soup = BeautifulSoup(page.content)
	trs = soup.find_all("tr")
	for no,tr in enumerate(trs):
		if no == 0:
			pass
		elif tr.get("class") == ['primary_colour']:
			pass
		else:
			try:
				house = {}
				try:
					thumb = tr.td.div.a.img.get("src")
					house["Image"] = thumb.replace("_ps.jpg",".jpg")
				except Exception as e:
					print e,link["Link"],'Image did not work'
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
				try:
					house["Auction"] = 'Auction' in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					if house["Auction"] == True:
						if " " in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip():
							date = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().split(" ")[1]
							house["Auction date"] = dateutil.parser.parse(date)
					house["Under offer"] = "Under offer" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					house["Negotiation"] = "(by negotiation)" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip() or "By Negotiation" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					house["Range"] = "-" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					if house["Range"] == True:
						house["Range low"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().split("-")[0].strip()
						house["Range high"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().split("-")[1].strip()
					house["Upwards of"] = u"+" in tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					if house["Upwards of"] == True:
						house["Price"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip().replace("+","")
					if house["Auction"] == False:
						if house["Under offer"] == False:
							if house["Negotiation"] == False:
								if house["Range"] == False:
									if house["Upwards of"] == False:
										house["Price"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
				except Exception as e:
					print e,link["Link"],'Something went wrong with the price for',tr.td.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
				try:
					house["Type"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
					house["EER"] = tr.td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text.strip()
				except Exception as e:
					print e,link["Link"],'Either the property type or EER did not work'
				try:
					house["Address 1"]=tr.td.next_sibling.next_sibling.div.div.a.text.split(",")[0]
					house["Suburb"]=link["Name"]
					house["Link"]=tr.td.next_sibling.next_sibling.div.div.a.get("href")
					house["Sold"] = tr.find("span",class_="badge-sold")!=None
					house["New"] = tr.find("span",class_="badge-new")!=None
					house["New price"] = tr.find("span",class_="badge-new-price")!=None
					house["When"] = datetime.datetime.now()
				except Exception as e:
					print e,link["Link"],'Something in the main box did not work'
			except Exception as e:
				print e,link["Link"],'Getting data did not work'
			lasthouse = scraperwiki.sql.select("* from data where Link=? order by 'When' desc limit 1",[house["Link"]])
			if lasthouse == []:
				dic = {}
				for k in house.keys():
					dic[k] = 'No value bro!'
				lasthouse.append(dic)
			same = True
			for h in house.keys():
				if h == 'When':
					pass
				else:
					if house[h] == True:
						house[h] = 1
					elif house[h] == False:
						house[h] = 0
					if h == 'Auction date':
						if lasthouse[0][h] == 'No value bro!':
							same = False
						else:
							if house[h] != dateutil.parser.parse(lasthouse[0][h]):
								same = False
					elif house[h] != lasthouse[0][h]:
						same = False
			if same == False:
				scraperwiki.sqlite.save(unique_keys=[],data=house,table_name='data')