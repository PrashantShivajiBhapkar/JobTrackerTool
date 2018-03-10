from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine
import PyPDF2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import pandas as pd
import datetime


def get_soup(url):
	http = urllib3.PoolManager()
	page = http.request('GET', url)
	soup = BeautifulSoup(page.data, 'lxml')
	return soup

def get_next_page_link(soup):
	pagination_links = []
	for div in soup.find_all(name="div", attrs={"class":"pagination"}):
		for a in div.find_all(name="a"):
			link = a["href"]
			if link != None:
				pagination_links.append(link)
	return('https://www.indeed.com' + pagination_links[len(pagination_links)-1])

def slice_soup(soup, sourceTagDict, job_header=False):
	# print(soup.find_all(list(sourceTagDict.keys())[0], list(sourceTagDict.values())[0]))
	if job_header:
		return soup.find(list(sourceTagDict.keys())[0], list(sourceTagDict.values())[0])
	else:
		return soup.find_all(list(sourceTagDict.keys())[0], list(sourceTagDict.values())[0])

def scraper(soup, sourceTagDict=None, text=False, get_url_list=False):    
    title = ''
    url_list = []
    scrapedContent = ''    
    
    if get_url_list:
    	for key, value in sourceTagDict.items():
    		for div in soup.find_all(key, value):
    			for a in div.find_all(name="a", attrs={"data-tn-element":"jobTitle"}):
    				link = a['href']
    				if link != None:
    					url_list.append('https://www.indeed.com' + link)
    	# print(url_list)
    	return list(set(url_list))

    	# for arr in range(len(soup)):
    	# 	a = soup[arr].find('a', href=True)
    	# 	urls.append('www.indeed.com' + a['href'])
    	# return urls
    elif text:  	
    	for (keyTag, attrVals) in sourceTagDict.items():
    		for tag in soup.find_all(keyTag, attrVals):
    			scrapedContent += ' ' + tag.get_text(strip=True)
    	return scrapedContent

def read_pdf(path):
	fp = open(path, 'rb')

	pdfFileObj = open(path,'rb')     #'rb' for read binary mode
	pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
	pypdf_text = ''
	for page_number in range(0, pdfReader.numPages):
		pageObj = pdfReader.getPage(page_number)
		pypdf_text += pageObj.extractText() + "\n"
	pypdf_text = " ".join(pypdf_text.replace(u"\xa0", " ").strip().split())

	parser = PDFParser(fp)
	doc = PDFDocument()
	parser.set_document(doc)
	doc.set_parser(parser)
	doc.initialize('')
	rsrcmgr = PDFResourceManager()
	laparams = LAParams()
	laparams.char_margin = 1.0
	laparams.word_margin = 1.0
	device = PDFPageAggregator(rsrcmgr, laparams=laparams)
	interpreter = PDFPageInterpreter(rsrcmgr, device)
	extracted_text = ''

	for page in doc.get_pages():
		interpreter.process_page(page)
		layout = device.get_result()
		for lt_obj in layout:
			if isinstance(lt_obj, LTTextBox) or isinstance(lt_obj, LTTextLine):
				extracted_text += lt_obj.get_text()
	return extracted_text, pypdf_text

def get_job_details(url_list, column_list, resume_skills_set, skills_set, posted_since_threshold=15
					, match_percentage_threshold=40):
	df = pd.DataFrame(columns = column_list)
	for url in url_list:
		soup = get_soup(url)
		
		job_description = scraper(soup, {'span': {'id':'job_summary', 'class':'summary'}}, text=True)
		
		soup_with_job_title = slice_soup(soup, {'div': {'data-tn-component':'jobHeader'}}, job_header=True)
		
		if(soup_with_job_title != None):
			job_title = scraper(soup_with_job_title, {'b': {"class":'jobtitle'}}, text=True)
			company = scraper(soup_with_job_title, {'span': {'class':'company'}}, text=True)	
			job_location = scraper(soup_with_job_title, {'span': {'class':'location'}}, text=True)
			job_type = scraper(soup_with_job_title, {'span': {'class':'no-wrap'}}, text=True)
			days_posted_ago = scraper(soup, {'span': {'class':'date'}}, text=True)
			posted_info = days_posted_ago.strip().split()
			second_word = posted_info[1]
			if second_word not in ['day', 'days']:
				days_posted_ago = round(int(posted_info[0])/24, 2)
			else:
				days_posted_ago = int(posted_info[0].replace('+',''))

			if days_posted_ago < posted_since_threshold:
			# get skills in the job description 
				job_skills_set = get_skills(job_description, skills_set)

				# Analyze the results
				skills_matched = job_skills_set & resume_skills_set
				skills_missing = job_skills_set - resume_skills_set
				irrelevant_extra_skills = resume_skills_set - job_skills_set
				n_job_skills = len(job_skills_set)
				n_resume_skills = len(resume_skills_set)
				n_skills_matched = len(skills_matched)
				n_skills_missing = len(skills_missing)
				n_irrelevant_extra_skills = len(irrelevant_extra_skills)
				match_percentage = round((n_skills_matched/n_job_skills)*100, 2)
								
				
				if match_percentage > match_percentage_threshold:
					df_temp = pd.DataFrame([[job_title, company, job_location, job_type, days_posted_ago 
											, match_percentage, url , n_job_skills
											, ', '.join(skill for skill in job_skills_set) 
											, n_skills_matched
											, ', '.join(skill for skill in skills_matched) 
											, n_skills_missing
											, ', '.join(skill for skill in skills_missing)  
											, n_irrelevant_extra_skills
											, ', '.join(skill for skill in irrelevant_extra_skills)  
											, n_resume_skills]], 
										columns=column_list)	
				
					df = df.append(df_temp)
	return df


def generate_skills_set():
	skills_set = set(['Administrative','Analysis','Analyzing Issues','Assessment','Attention to Detail','Attentive Listening','Budgeting','Business Intelligence','Collaboration','Communication','Concision','Confidence','Coordinating','Coordination','Creative','Creative Thinking','Data','Data Trends','Deadlines','Decision Making','Delegation','Design','Development','Difference Resolution','Directing Others','Documentation','Effectiveness','Evaluating','Facilitating','Forecasting','Goals','Goal Setting','Group Leadership','Handling Details','Identifying Problems','Identifying Resources','Implementation','Implementing Decisions','Information Gathering','Instruction','Leadership','Management','Managing Appointments','Managing Conflict','Meeting Deadlines','Meeting Goals','Metrics','Microsoft Office','Motivational','Multitasking','Negotiation','Oral Communication','Organization','Organization Development','Persuasion','Plan Development','Planning','Policy Enforcement','Predicting','Presentation','Prioritization','Problem Solving','Productivity','Program Management','Project Management','Providing Feedback','Public Speaking','Research','Responsibility','Review','Scheduling','Situational Assessment','Strategic Planning','Strategy Development','Structural Planning','Succession Planning','Taking Charge','Task Analysis','Task Assessment','Task Resolution','Teaching','Team Building','Teamwork','Time Management','Training','Trends','Workflow Analysis','Workflow Management','Workforce Analysis','Working with Others','Writing','Able to ignore extraneous information','Abstract thinking','Analytical','Analyze and diagnose complex situations','Break down a project into manageable pieces','Broad thinking','Cognitive abilities','Committed to achieving company goals','Communication','Contextualize problems','Creative thinking','Critical thinking','Decision making','Define strategies for reaching goals','Delegation','Diagnose problems within the company','Effectively communicate strategy','Examine complex issues','Execute solutions','Formulate effective course of action','Formulate ideas','Formulate processes','Implement thinking','Innovation','Intuitive thinking','Interrelational','Leadership','Logical thinking','Management','Motivation','Multitasking','Organization','Persuasive','Predict the future of the business or department','Presentation','Prioritization','Problem-solving','Question the connection between new initiatives and the strategic plan','Recognize opportunities for improvement','Resolve industry problems','See the key elements in any situation','Select important information from large amounts of data','Stability','Strategic planning','Task direction','Task implementation','Team building','Understand relationships between departments','Understand relationships between ideas',' concepts',' and patterns','Understand the organization’s business model','Verbal communication','Vision','Visualize the company as a whole','Empathy','Cooperation','Verbal Communication','Listening','Nonverbal Communication','Accounting','Administrative','Analysis','Analytics','Automotive','Banking','Bookkeeping','Carpentry','Computer','Construction','Data','Design','Editing','Electrical','Engineering','Financial','Hardware','Healthcare','Information Technology','Languages','Legal','Manufacturing','Math','Mechanical','Medical','Nursing','Optimization','Pharmaceutical','Pipefitter','Plumbing','Project Management','Programming','Research','Reporting','Science','Software','Spreadsheets','Teaching','Technology','Testing','Translation','Transcription','Word Processing','Writing','Adaptability','Advanced Microsoft Excel','Advanced SQL','Amazon Web Services (AWS)','Analytical','Analytical Solutions','Analytics','Applying Knowledge of the Software Development Lifecycle ','Assessing the Data Needs of Internal Stakeholders or Clients','Attention to Detail','Big Data Solutions','Big Data Strategy','Big Data Technologies','Coaching Executives Regarding the Impact of Big Data on Strategic Plans','Cloud Computing','Collaboration','Communication','Conducting Statistical Analyses','Continual Learning','Conveying Technical Information to Non-Technical Audiences','Creating Visualizations for Data Systems','Creative Thinking','Critical Thinking','Data Access Systems','Data Architecture','Data Flow','Data Management','Data Mining','Data Modeling','Data Profiling','Data Sets','Data Wrangling','Decision Making Regarding Complex Technical Designs','Designing Data Warehouses','Drafting Proposals','Drawing Consensus','Estimating Costs for Projects','Facilitating Group Discussion','Hadoop','Handling Criticism Non-Defensively','Implementing Data Warehouse Systems','Interpreting Data Output','Large Data Sets','Leadership','Leading Cross-Functional Groups','Manipulating Relational Databases','Matlab','Multitasking','NoSQL','Organizational','Persuading Colleagues to Adopt Preferred Big Data Systems and Strategies','PowerPoint ','Presentation to Groups','Problem Solving','Programming with Java','Project Management','Python','Quantitative','R','Research','SAS','Shell Scripting','Spark','SPSS','Stress Management','Structuring Cloud Storage Solutions for Big Data','Taking Initiative','Teamwork','Time Management','Tracking Trends and Emerging Developments in Big Data','Translating Data Analysis into Key Insights','Verbal Communication','Visualizations','Working Independently','Writing Reports with Data Findings','Adaptability','Algorithms','Algorithmic','Analytical','Analytical Tools','Analytics','AppEngine','Assertiveness','AWS','Big Data','C++','Collaboration ','Communication','Computer Skills','Constructing Predictive Models','Consulting','Conveying Technical Information to Non-Technical People','CouchDB','Creating Algorithms','Creating Controls to Assure Accuracy of Data','Creativity','Critical Thinking','Cultivating Relationships with Internal and External Stakeholders','Customer Service','Data','Data Analysis','Data Analytics','Data Manipulation','Data Wrangling','Data Science Tools','Data Tools','Data Mining','D3.js','Decision Making','Decision Trees','Development','Documenting','Drawing Consensus','ECL','Evaluating New Analytical Methodologies','Executing in a Fast-Paced Environment','Facilitating Meetings','Flare','Google Visualization API','Hadoop','HBase','High Energy','Information Retrieval Data Sets','Interpreting Data','Java','Leadership','Linear Algebra','Logical Thinking','Machine Learning Models','Machine Learning Techniques','Mathematics','Matlab','Mentoring','Metrics','Microsoft Excel','Mining Social Media Data','Modeling Data','Modeling Tools','Multivariable Calculus','Perl','PowerPoint','Presentation','Problem Solving','Producing Data Visualizations','Project Management','Project Management Methodologies','Project Timelines','Programming','Providing Guidance to IT Professionals','Python','R','Raphael.js','Reporting','Reporting Tool Software','Reporting Tools','Reports','Research','Researching','Risk Modeling','SAS','Scripting Languages','Self Motivated','SQL','Statistics','Statistical Learning Models','Statistical Modeling','Supervisory','Tableau','Taking Initiative','Testing Hypotheses','Training','Verbal','Working Independently','Writing','Assign Passwords and Maintain Database Access','Agile Development','Agile Project Methodology','Amazon Web Services (AWS)','Analytics','Analytical','Analyze and Recommend Database Improvements','Analyze Impact of Database Changes to the Business','Audit Database Access and Requests','APIs','Application and Server Monitoring Tools','Applications','Application Development','Attention to Detail','Architecture','Big Data','Business Analytics','Business Intelligence','Business Process Modeling','Cloud Applications','Cloud Based Visualizations','Cloud Hosting Services','Cloud Maintenance Tasks','Cloud Management Tools','Cloud Platforms','Cloud Scalability','Cloud Services','Cloud Systems Administration','Code','Coding','Computer','Communication','Configure Database Software','Configuration','Configuration Management','Content Strategy','Content Management','Continually Review Processes for Improvement ','Continuous Deployment','Continuous Integration','Critical Thinking','Customer Support','Database','Data Analysis','Data Analytics','Data Imports','Data Imports','Data Intelligence','Data Mining','Data Modeling','Data Science','Data Strategy','Data Storage','Data Visualization Tools','Data Visualizations','Database Administration','Deploying Applications in a Cloud Environment','Deployment Automation Tools','Deployment of Cloud Services','Design','Desktop Support','Design','Design and Build Database Management System','Design Principles','Design Prototypes','Design Specifications','Design Tools','Develop and Secure Network Structures','Develop and Test Methods to Synchronize Data ','Developer','Development','Documentation','Emerging Technologies','File Systems','Flexibility','Front End Design','Google Analytics','Hardware','Help Desk','Identify User Needs ','Implement Backup and Recovery Plan ','Implementation','Information Architecture','Information Design','Information Systems','Interaction Design','Interaction Flows','Install',' Maintain',' and Merge Databases ','Installation','Integrated Technologies','Integrating Security Protocols with Cloud Design','Internet','IT Optimization','IT Security','IT Soft Skills','IT Solutions','IT Support','Languages','Logical Thinking','Leadership','Linux','Management','Messaging','Methodology','Metrics','Microsoft Office','Migrating Existing Workloads into Cloud Systems','Mobile Applications','Motivation','Networks','Network Operations','Networking','Open Source Technology Integration','Operating Systems','Operations','Optimize Queries on Live Data','Optimizing User Experiences','Optimizing Website Performance','Organization','Presentation','Programming','Problem Solving','Process Flows','Product Design','Product Development','Prototyping Methods','Product Development','Product Management','Product Support','Product Training','Project Management','Repairs','Reporting','Research Emerging Technology','Responsive Design','Review Existing Solutions','Search Engine Optimization (SEO)','Security','Self Motivated','Self Starting','Servers','Software','Software Development','Software Engineering','Software Quality Assurance (QA)','Solid Project Management Capabilities ','Solid Understanding of Company’s Data Needs ','Storage','Strong Technical and Interpersonal Communication ','Support','Systems Software','Tablets','Team Building','Team Oriented','Teamwork','Technology','Tech Skills','Technical Support','Technical Writing','Testing','Time Management','Tools','Touch Input Navigation','Training','Troubleshooting','Troubleshooting Break-Fix Scenarios','User Research','User Testing','Usability','User-Centered Design','User Experience','User Flows','User Interface','User Interaction Diagrams','User Research','User Testing','UI / UX','Utilizing Cloud Automation Tools','Virtualization','Visual Design','Web Analytics','Web Applications','Web Development','Web Design','Web Technologies','Wireframes','Work Independently','Adobe Illustrator','Adobe InDesign','Adobe Photoshop','Analytics','Android','APIs','Art Design','AutoCAD','Backup Management','C','C++','Certifications','Client Server','Client Support','Configuration','Content Managment','Content Management Systems (CMS)','Corel Draw','Corel Word Perfect','CSS','Data Analytics','Desktop Publishing','Design','Diagnostics','Documentation','End User Support','Email','Engineering','Excel','FileMaker Pro','Fortran','Graphic Design','Hardware','Help Desk','HTML','Implementation','Installation','Internet','iOS','iPhone','Linux','Java','Javascript','Mac','Matlab','Maya','Microsoft Excel','Microsoft Office','Microsoft Outlook','Microsoft Publisher','Microsoft Word','Microsoft Visual','Mobile','MySQL','Networks','Open Source Software','Oracle','Perl','PHP','Presentations','Processing','Programming','PT Modeler','Python','QuickBooks','Ruby','Shade','Software','Spreadsheet','SQL','Support','Systems Administration','Tech Support','Troubleshooting','Unix','UI/UX','Web Page Design','Windows','Word Processing','XML','XHTML','Algorithms','Analysis','Analytical','Analytics','Analyze Data','Applications','Application Development','Application Development Methodologies','Application Development Techniques','Application Development Tools','Application Programming Interfaces','Architecture','AROS','Ars Based Programming','Aspect Oriented Programming','Best Practices','Browsers','CASE Tools','Code','Coding','Collaboration','Communication','Components','Computer Platforms','Concurrent Programming','Computer Science','Constraint-based Programming','Customer Service','Database Management Systems (DBMS)','Database Techniques','Databases','Data','Data Analytics','Data Structures','Debugging','Design','Development','Development Tools','Documentation','Embedded Hardware','Emerging Technologies','Fourth Generation Languages','Hardware','HTML Authoring Tools','HTML Conversion Tools','Industry Systems','iOS','Information Systems','Implementation','Interface with Clients','Interface with Vendors','Internet','Languages','Linux','Logic','MacOS','Math','Mobile','Multimedia','Multi-Tasking','Operating Systems','Optimizing','Organizational','OS Programming','Parallel Processing','Personal','Physics','Planning','Post Object Programming','Problem Solving','Programming Languages','Programming Methodologies','Quality Control','Relational Databases','Relational Programming','Reporting','Revision Control','Self-Motivation','Software','Structured Query Language (SQL)','Symbolic Programming','System Architecture','System Development','System Design','System Programming','System Testing','Teamwork','Technical','Testing','Third Generation Languages','Troubleshooting','UNIX','Use Logical Reasoning','Web','Web Applications','Web Platforms','Web Services','Windowing Systems','Windows','Workstations','Ability to Adapt and Quickly Adjust to Change','Ability to Work in Fast Paced Environment','Ability to Work with Cross-Functional Teams','Analytical ','Assessment','Attention to Detail ','Creativity','Creative Thinking','Critical Thinking','Defining Problems ','Detail Oriented','Decision Making','Diplomatic','Innovation','Instructing','Leadership','Listening','Meeting Deadlines','Multi-Tasking','Organizational Skills','Planning','Prioritizing','Written Communication','Building Consensus','Client Relationship Management','Collaboration','Communication','Conflict Resolution','Customer Service','Influencing Others','Interviewing','Negotiation','Teamwork','Verbal Communication','Presentation','Facilitating Meetings','Follow-Up','Navigating a Matrix Reporting Relationship','Executing Change','Microsoft Access','Microsoft Excel','Microsoft Office','Microsoft Project','PowerPoint','SharePoint','SQL Queries','Software Design Tools','Visio','Designing and Implementing Tests of Processes','Forecasting','Gap Analysis','Documentation','Quantitative','Reporting','Research','Risk Assessment','Statistical Analysis','Taking Initiative','Technical Integration','Validate Functionality','Problem Solving','Process Mapping','Process Modeling','Project Management','Data Review','Visualizations','Eliciting and specifying project requirements','Financial Planning', 'Python','SQL','PLSQL','Java','C#','C','C++','R','Spyder','Jupyter Notebooks','R-Studio','Oracle SQL Developer','Toad','MS Visual Studio','Hadoop ecosystem','Pig','Hive','Spark','Sqoop','Flume','MapReduce','Hadoop Streaming','Microsoft Azure','sci-kit learn','sklearn','Tensorflow','Keras','Numpy','Pandas','Matplotlib','Seaborn','NLTK','SAS','Enterprise Miner','Big Data Analytics','Data Mining','Predictive Quantitative Analysis','Forecasting','Business Intelligence','Decision Analytics','ETL','Data Analysis','Machine Learning Algorithms','Multivariate Analysis','Statistics','Statistical Modelling','Data Visualization','SAP HANA','Tableau','Lumira','SAP Business Objects','OLAP','SAP Design Studio','Business Objects','BEX Query Designer and Analyzer','SAP NetWeaver','Data Warehousing','MS Excel','Reporting','Exploratory Data Analysis','Statistical Analysis','Quantitative Analysis','Statistical Learning','Text Analytics','Windows','Linux','Convolutional Neural Network','CNN','image classification problem','image classification','Image Processing','HANA', 'EDA'])
	return skills_set

def get_skills(input_object, skills_set):
	object_skills = []
	for skill in skills_set:
		if skill.lower() in input_object.lower():
			object_skills.append(skill)
	return set(object_skills)


def main(resume, search_string, n_pages_to_scrape, posted_since_threshold=15
		 , match_percentage_threshold=40):

	dict_to_mail = {}
	# skills_set = set(['Administrative','Analysis','Analyzing Issues','Assessment','Attention to Detail','Attentive Listening','Budgeting','Business Intelligence','Collaboration','Communication','Concision','Confidence','Coordinating','Coordination','Creative','Creative Thinking','Data','Data Trends','Deadlines','Decision Making','Delegation','Design','Development','Difference Resolution','Directing Others','Documentation','Effectiveness','Evaluating','Facilitating','Forecasting','Goals','Goal Setting','Group Leadership','Handling Details','Identifying Problems','Identifying Resources','Implementation','Implementing Decisions','Information Gathering','Instruction','Leadership','Management','Managing Appointments','Managing Conflict','Meeting Deadlines','Meeting Goals','Metrics','Microsoft Office','Motivational','Multitasking','Negotiation','Oral Communication','Organization','Organization Development','Persuasion','Plan Development','Planning','Policy Enforcement','Predicting','Presentation','Prioritization','Problem Solving','Productivity','Program Management','Project Management','Providing Feedback','Public Speaking','Research','Responsibility','Review','Scheduling','Situational Assessment','Strategic Planning','Strategy Development','Structural Planning','Succession Planning','Taking Charge','Task Analysis','Task Assessment','Task Resolution','Teaching','Team Building','Teamwork','Time Management','Training','Trends','Workflow Analysis','Workflow Management','Workforce Analysis','Working with Others','Writing','Able to ignore extraneous information','Abstract thinking','Analytical','Analyze and diagnose complex situations','Break down a project into manageable pieces','Broad thinking','Cognitive abilities','Committed to achieving company goals','Communication','Contextualize problems','Creative thinking','Critical thinking','Decision making','Define strategies for reaching goals','Delegation','Diagnose problems within the company','Effectively communicate strategy','Examine complex issues','Execute solutions','Formulate effective course of action','Formulate ideas','Formulate processes','Implement thinking','Innovation','Intuitive thinking','Interrelational','Leadership','Logical thinking','Management','Motivation','Multitasking','Organization','Persuasive','Predict the future of the business or department','Presentation','Prioritization','Problem-solving','Question the connection between new initiatives and the strategic plan','Recognize opportunities for improvement','Resolve industry problems','See the key elements in any situation','Select important information from large amounts of data','Stability','Strategic planning','Task direction','Task implementation','Team building','Understand relationships between departments','Understand relationships between ideas',' concepts',' and patterns','Understand the organization’s business model','Verbal communication','Vision','Visualize the company as a whole','Empathy','Cooperation','Verbal Communication','Listening','Nonverbal Communication','Accounting','Administrative','Analysis','Analytics','Automotive','Banking','Bookkeeping','Carpentry','Computer','Construction','Data','Design','Editing','Electrical','Engineering','Financial','Hardware','Healthcare','Information Technology','Languages','Legal','Manufacturing','Math','Mechanical','Medical','Nursing','Optimization','Pharmaceutical','Pipefitter','Plumbing','Project Management','Programming','Research','Reporting','Science','Software','Spreadsheets','Teaching','Technology','Testing','Translation','Transcription','Word Processing','Writing','Adaptability','Advanced Microsoft Excel','Advanced SQL','Amazon Web Services (AWS)','Analytical','Analytical Solutions','Analytics','Applying Knowledge of the Software Development Lifecycle ','Assessing the Data Needs of Internal Stakeholders or Clients','Attention to Detail','Big Data Solutions','Big Data Strategy','Big Data Technologies','Coaching Executives Regarding the Impact of Big Data on Strategic Plans','Cloud Computing','Collaboration','Communication','Conducting Statistical Analyses','Continual Learning','Conveying Technical Information to Non-Technical Audiences','Creating Visualizations for Data Systems','Creative Thinking','Critical Thinking','Data Access Systems','Data Architecture','Data Flow','Data Management','Data Mining','Data Modeling','Data Profiling','Data Sets','Data Wrangling','Decision Making Regarding Complex Technical Designs','Designing Data Warehouses','Drafting Proposals','Drawing Consensus','Estimating Costs for Projects','Facilitating Group Discussion','Hadoop','Handling Criticism Non-Defensively','Implementing Data Warehouse Systems','Interpreting Data Output','Large Data Sets','Leadership','Leading Cross-Functional Groups','Manipulating Relational Databases','Matlab','Multitasking','NoSQL','Organizational','Persuading Colleagues to Adopt Preferred Big Data Systems and Strategies','PowerPoint ','Presentation to Groups','Problem Solving','Programming with Java','Project Management','Python','Quantitative','R','Research','SAS','Shell Scripting','Spark','SPSS','Stress Management','Structuring Cloud Storage Solutions for Big Data','Taking Initiative','Teamwork','Time Management','Tracking Trends and Emerging Developments in Big Data','Translating Data Analysis into Key Insights','Verbal Communication','Visualizations','Working Independently','Writing Reports with Data Findings','Adaptability','Algorithms','Algorithmic','Analytical','Analytical Tools','Analytics','AppEngine','Assertiveness','AWS','Big Data','C++','Collaboration ','Communication','Computer Skills','Constructing Predictive Models','Consulting','Conveying Technical Information to Non-Technical People','CouchDB','Creating Algorithms','Creating Controls to Assure Accuracy of Data','Creativity','Critical Thinking','Cultivating Relationships with Internal and External Stakeholders','Customer Service','Data','Data Analysis','Data Analytics','Data Manipulation','Data Wrangling','Data Science Tools','Data Tools','Data Mining','D3.js','Decision Making','Decision Trees','Development','Documenting','Drawing Consensus','ECL','Evaluating New Analytical Methodologies','Executing in a Fast-Paced Environment','Facilitating Meetings','Flare','Google Visualization API','Hadoop','HBase','High Energy','Information Retrieval Data Sets','Interpreting Data','Java','Leadership','Linear Algebra','Logical Thinking','Machine Learning Models','Machine Learning Techniques','Mathematics','Matlab','Mentoring','Metrics','Microsoft Excel','Mining Social Media Data','Modeling Data','Modeling Tools','Multivariable Calculus','Perl','PowerPoint','Presentation','Problem Solving','Producing Data Visualizations','Project Management','Project Management Methodologies','Project Timelines','Programming','Providing Guidance to IT Professionals','Python','R','Raphael.js','Reporting','Reporting Tool Software','Reporting Tools','Reports','Research','Researching','Risk Modeling','SAS','Scripting Languages','Self Motivated','SQL','Statistics','Statistical Learning Models','Statistical Modeling','Supervisory','Tableau','Taking Initiative','Testing Hypotheses','Training','Verbal','Working Independently','Writing','Assign Passwords and Maintain Database Access','Agile Development','Agile Project Methodology','Amazon Web Services (AWS)','Analytics','Analytical','Analyze and Recommend Database Improvements','Analyze Impact of Database Changes to the Business','Audit Database Access and Requests','APIs','Application and Server Monitoring Tools','Applications','Application Development','Attention to Detail','Architecture','Big Data','Business Analytics','Business Intelligence','Business Process Modeling','Cloud Applications','Cloud Based Visualizations','Cloud Hosting Services','Cloud Maintenance Tasks','Cloud Management Tools','Cloud Platforms','Cloud Scalability','Cloud Services','Cloud Systems Administration','Code','Coding','Computer','Communication','Configure Database Software','Configuration','Configuration Management','Content Strategy','Content Management','Continually Review Processes for Improvement ','Continuous Deployment','Continuous Integration','Critical Thinking','Customer Support','Database','Data Analysis','Data Analytics','Data Imports','Data Imports','Data Intelligence','Data Mining','Data Modeling','Data Science','Data Strategy','Data Storage','Data Visualization Tools','Data Visualizations','Database Administration','Deploying Applications in a Cloud Environment','Deployment Automation Tools','Deployment of Cloud Services','Design','Desktop Support','Design','Design and Build Database Management System','Design Principles','Design Prototypes','Design Specifications','Design Tools','Develop and Secure Network Structures','Develop and Test Methods to Synchronize Data ','Developer','Development','Documentation','Emerging Technologies','File Systems','Flexibility','Front End Design','Google Analytics','Hardware','Help Desk','Identify User Needs ','Implement Backup and Recovery Plan ','Implementation','Information Architecture','Information Design','Information Systems','Interaction Design','Interaction Flows','Install',' Maintain',' and Merge Databases ','Installation','Integrated Technologies','Integrating Security Protocols with Cloud Design','Internet','IT Optimization','IT Security','IT Soft Skills','IT Solutions','IT Support','Languages','Logical Thinking','Leadership','Linux','Management','Messaging','Methodology','Metrics','Microsoft Office','Migrating Existing Workloads into Cloud Systems','Mobile Applications','Motivation','Networks','Network Operations','Networking','Open Source Technology Integration','Operating Systems','Operations','Optimize Queries on Live Data','Optimizing User Experiences','Optimizing Website Performance','Organization','Presentation','Programming','Problem Solving','Process Flows','Product Design','Product Development','Prototyping Methods','Product Development','Product Management','Product Support','Product Training','Project Management','Repairs','Reporting','Research Emerging Technology','Responsive Design','Review Existing Solutions','Search Engine Optimization (SEO)','Security','Self Motivated','Self Starting','Servers','Software','Software Development','Software Engineering','Software Quality Assurance (QA)','Solid Project Management Capabilities ','Solid Understanding of Company’s Data Needs ','Storage','Strong Technical and Interpersonal Communication ','Support','Systems Software','Tablets','Team Building','Team Oriented','Teamwork','Technology','Tech Skills','Technical Support','Technical Writing','Testing','Time Management','Tools','Touch Input Navigation','Training','Troubleshooting','Troubleshooting Break-Fix Scenarios','User Research','User Testing','Usability','User-Centered Design','User Experience','User Flows','User Interface','User Interaction Diagrams','User Research','User Testing','UI / UX','Utilizing Cloud Automation Tools','Virtualization','Visual Design','Web Analytics','Web Applications','Web Development','Web Design','Web Technologies','Wireframes','Work Independently','Adobe Illustrator','Adobe InDesign','Adobe Photoshop','Analytics','Android','APIs','Art Design','AutoCAD','Backup Management','C','C++','Certifications','Client Server','Client Support','Configuration','Content Managment','Content Management Systems (CMS)','Corel Draw','Corel Word Perfect','CSS','Data Analytics','Desktop Publishing','Design','Diagnostics','Documentation','End User Support','Email','Engineering','Excel','FileMaker Pro','Fortran','Graphic Design','Hardware','Help Desk','HTML','Implementation','Installation','Internet','iOS','iPhone','Linux','Java','Javascript','Mac','Matlab','Maya','Microsoft Excel','Microsoft Office','Microsoft Outlook','Microsoft Publisher','Microsoft Word','Microsoft Visual','Mobile','MySQL','Networks','Open Source Software','Oracle','Perl','PHP','Presentations','Processing','Programming','PT Modeler','Python','QuickBooks','Ruby','Shade','Software','Spreadsheet','SQL','Support','Systems Administration','Tech Support','Troubleshooting','Unix','UI/UX','Web Page Design','Windows','Word Processing','XML','XHTML','Algorithms','Analysis','Analytical','Analytics','Analyze Data','Applications','Application Development','Application Development Methodologies','Application Development Techniques','Application Development Tools','Application Programming Interfaces','Architecture','AROS','Ars Based Programming','Aspect Oriented Programming','Best Practices','Browsers','CASE Tools','Code','Coding','Collaboration','Communication','Components','Computer Platforms','Concurrent Programming','Computer Science','Constraint-based Programming','Customer Service','Database Management Systems (DBMS)','Database Techniques','Databases','Data','Data Analytics','Data Structures','Debugging','Design','Development','Development Tools','Documentation','Embedded Hardware','Emerging Technologies','Fourth Generation Languages','Hardware','HTML Authoring Tools','HTML Conversion Tools','Industry Systems','iOS','Information Systems','Implementation','Interface with Clients','Interface with Vendors','Internet','Languages','Linux','Logic','MacOS','Math','Mobile','Multimedia','Multi-Tasking','Operating Systems','Optimizing','Organizational','OS Programming','Parallel Processing','Personal','Physics','Planning','Post Object Programming','Problem Solving','Programming Languages','Programming Methodologies','Quality Control','Relational Databases','Relational Programming','Reporting','Revision Control','Self-Motivation','Software','Structured Query Language (SQL)','Symbolic Programming','System Architecture','System Development','System Design','System Programming','System Testing','Teamwork','Technical','Testing','Third Generation Languages','Troubleshooting','UNIX','Use Logical Reasoning','Web','Web Applications','Web Platforms','Web Services','Windowing Systems','Windows','Workstations','Ability to Adapt and Quickly Adjust to Change','Ability to Work in Fast Paced Environment','Ability to Work with Cross-Functional Teams','Analytical ','Assessment','Attention to Detail ','Creativity','Creative Thinking','Critical Thinking','Defining Problems ','Detail Oriented','Decision Making','Diplomatic','Innovation','Instructing','Leadership','Listening','Meeting Deadlines','Multi-Tasking','Organizational Skills','Planning','Prioritizing','Written Communication','Building Consensus','Client Relationship Management','Collaboration','Communication','Conflict Resolution','Customer Service','Influencing Others','Interviewing','Negotiation','Teamwork','Verbal Communication','Presentation','Facilitating Meetings','Follow-Up','Navigating a Matrix Reporting Relationship','Executing Change','Microsoft Access','Microsoft Excel','Microsoft Office','Microsoft Project','PowerPoint','SharePoint','SQL Queries','Software Design Tools','Visio','Designing and Implementing Tests of Processes','Forecasting','Gap Analysis','Documentation','Quantitative','Reporting','Research','Risk Assessment','Statistical Analysis','Taking Initiative','Technical Integration','Validate Functionality','Problem Solving','Process Mapping','Process Modeling','Project Management','Data Review','Visualizations','Eliciting and specifying project requirements','Financial Planning', 'Python','SQL','PLSQL','Java','C#','C','C++','R','Spyder','Jupyter Notebooks','R-Studio','Oracle SQL Developer','Toad','MS Visual Studio','Hadoop ecosystem','Pig','Hive','Spark','Sqoop','Flume','MapReduce','Hadoop Streaming','Microsoft Azure','sci-kit learn','sklearn','Tensorflow','Keras','Numpy','Pandas','Matplotlib','Seaborn','NLTK','SAS','Enterprise Miner','Big Data Analytics','Data Mining','Predictive Quantitative Analysis','Forecasting','Business Intelligence','Decision Analytics','ETL','Data Analysis','Machine Learning Algorithms','Multivariate Analysis','Statistics','Statistical Modelling','Data Visualization','SAP HANA','Tableau','Lumira','SAP Business Objects','OLAP','SAP Design Studio','Business Objects','BEX Query Designer and Analyzer','SAP NetWeaver','Data Warehousing','MS Excel','Reporting','Exploratory Data Analysis','Statistical Analysis','Quantitative Analysis','Statistical Learning','Text Analytics','Windows','Linux','Convolutional Neural Network','CNN','image classification problem','image classification','Image Processing','HANA', 'EDA'])
	skills_set = generate_skills_set()
	text, pypdf_text = read_pdf(resume)
	resume = text.strip()
	resume_skills = []

	# Get skills from resume
	# for skill in skills_set:
	# 	if skill.lower() in resume.lower():
	# 		resume_skills.append(skill)
	# resume_skills_set = set(resume_skills)
	resume_skills_set = get_skills(resume, skills_set)

	# URLs of indeed jobs
	# main_page_url = 'https://www.indeed.com/q-Summer-Data-Science-Internship-jobs.html'
	search_keywords = search_string.strip().split()
	main_page_url_end = '+'.join(keyword for keyword in search_keywords)
	main_page_url = 'https://www.indeed.com/jobs?q=' + main_page_url_end + '&l='
	
	column_list = ['JobTitle', 'company', 'JobLocation', 'JobType', 'DaysPostedAgo', 'MatchPercentage'
		, 'LinkToApply', 'NoOfSkillsJobDemanded', 'SkillsJobDemended', 'NoOfMatchedSkills', 'MatchedSkills', 'NoOfUnmatchedSkills'
		 , 'UnmatchedSkills', 'NoOfExtraSkillsYouHave', 'ExtraSkillsYouHave', 'MyTotalSkills']
	focused_jobs = pd.DataFrame(columns = column_list)

	iter_url = main_page_url
	print('')
	print('==> NOW consuming Job details for {0}'.format(search_string.upper())+" Positions <==")	

	for i in range(n_pages_to_scrape):
		print('-Fetching Jobs from Indeed (Page-{0}) at this URL==>'.format(str(i+1)), iter_url)
		soup = get_soup(iter_url)		
		url_list = scraper(soup, {'div': {'class':'row'}}, get_url_list=True)
		focused_jobs = focused_jobs.append(get_job_details(url_list, column_list, resume_skills_set,
															 skills_set, posted_since_threshold,
															 match_percentage_threshold))
		iter_url = get_next_page_link(soup)
		
	focused_jobs = focused_jobs.sort_values(by=['MatchPercentage', 'DaysPostedAgo'], ascending=[False, True])
	focused_jobs.to_csv('C:/GitProjects/ResumeMatcher/Jobs to Focus/' + 
				'_'.join(keyword for keyword in search_keywords) + 
				'_JobsForYouOn_' + datetime.datetime.today().strftime("%b %d %Y").replace(' ','_') + 
				'.csv', sep=',', encoding='utf-8', 
						index=False)
	print('Jobs relevant to ' + search_string.upper() + ' Positions Consumed and written to '
			'C:/GitProjects/ResumeMatcher/Jobs to Focus/' + 
			'_'.join(keyword for keyword in search_keywords) + 
			'_JobsForYouOn_' + datetime.datetime.today().strftime("%b %d %Y").replace(' ','_') + 
			'.csv' )
	print('---------------------------------------------------------')
	return focused_jobs
	

if __name__ == '__main__':
	format = "%H:%M:%S %a, %b-%d-%Y"
	
	resume = 'C:/GitProjects/ResumeMatcher/Sample Resume/Resume_Abhishek_Magotra.pdf'
	match_percentage_threshold = 50
	days_posted_ago_threshold = 15
	n_pages = 2
	
	print("============= JOB CONSUMPTION STARTED AT " + 
		str(datetime.datetime.strptime(datetime.datetime.today().strftime(format), format).strftime(format)) +
		" =============")

	da_df = main(resume, 'Data Analyst Intern', n_pages, days_posted_ago_threshold, match_percentage_threshold)
	# ds_df = main(resume, 'Data Science Intern', n_pages, days_posted_ago_threshold, match_percentage_threshold)
	# ml_df = main(resume, 'Machine Learning Intern', n_pages, days_posted_ago_threshold, match_percentage_threshold)
	# dl_df = main(resume, 'Deep Learning Intern', n_pages, days_posted_ago_threshold, match_percentage_threshold)
	

	print('')
	print('============= SUMMARY =============')
	print('--NOTE: All the following details are of those jobs that match at least {0}% '.format(match_percentage_threshold)+
		'with your profile in terms of skills and are posted no longer than {0} days ago.'.format(days_posted_ago_threshold))
	print('==> Total' + ' Data Analyst Intern'.upper() + ' jobs consumed: 		{0}'.format(len(da_df)))
	print('==> Total' + ' Machine Learning Intern'.upper() + ' jobs consumed: 	{0}'.format(len(ml_df)))
	print('==> Total' + ' Deep Learning Intern'.upper() + ' jobs consumed: 		{0}'.format(len(dl_df)))
	print('==> Total' + ' Data Science Intern'.upper() + ' jobs consumed:: 		{0}'.format(len(ds_df)))
	print('')

	print("============= JOB CONSUMPTION ENDED AT " + 
		datetime.datetime.strptime(datetime.datetime.today().strftime(format), format).strftime(format) +
		" =============")



