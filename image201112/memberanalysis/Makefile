all: attend.png attend-r.csv

debmtg.db: memberls.csv postwork.csv prework.csv
	./sqlite-import.py

attend.csv: debmtg.db sqlite-attend.sh
	./sqlite-attend.sh

attend.png: attend.csv attend.py
	./attend.py

attend-r.csv: attend.csv
	(echo "year,month,attend,prework,postwork"; cat attend.csv ) > attend-r.csv

kansai.png: kansai.csv attend-kansai.py
	./attend-kansai.py
