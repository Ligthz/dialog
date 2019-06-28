from django.shortcuts import render
import requests
from django.views.generic import TemplateView
from django.core.files.storage import FileSystemStorage
import patoolib
import os
import openpyxl
import csv
from os import listdir
from . import settings
from os.path import isfile, join
import shutil
from django import forms
import string
import random
import datetime
import re


class parameter:
    def __init__(self,book,site):
        self.parameter=[]
        self.data_row = 0
        self.data_col = 0
        self.data = {}
        trigger = 0
        for rw in book:
            cells = rw.split(",")
            cells[-1] = cells[-1].rstrip("\n")
            if "Sample Name" in cells[0]:
                self.parameter.append("Site")
                for cell in cells:
                    self.parameter.append(cell)
                    self.data_col += 1
                    self.data[self.parameter[-1]] = []
                    if "Description" in cell:
                        self.parameter.append("Time")
                        self.data_col += 1
                self.data["Site"] = []
                self.data["Time"] = []
                trigger = 1
            elif trigger == 1:
                if cells[0] == "":
                    pass
                    #print("Found Empty Cell at "+str(book))
                else:
                    data_buf=[]
                    for cell in cells:
                        data_buf.append(cell)
                    if "" in data_buf:
                        pass
                    else:
                        self.data["Site"].append(site)
                        col = 1
                        for k,cell in enumerate(data_buf):
                            if k==1:
                                self.data["Description"].append(cell)
                            if self.parameter[col] == "Sample Name":
                                cell = cell.replace("-","_")
                                cell = cell.replace(" ","")
                                self.data[self.parameter[col]].append(cell)
                                # append Time from sameple name
                                splitted_cell = data_buf[k].split("_")
                                if len(splitted_cell)==5: # Input Time from sample
                                    time = splitted_cell[-1]
                                    time_int = int(time) 
                                    if time_int>1200:
                                        time_int = int(time[0:2])-12
                                        time_stamp = str(time_int)+":"+time[2:4]+" PM"
                                    else:
                                        time_int = int(time[0:2])
                                        time_stamp = str(time_int)+":"+time[2:4]+" AM"
                                    self.data["Time"].append(time_stamp)
                                else:
                                    self.data["Time"].append("-")
                                col+=1
                            elif self.parameter[col] == "Time":
                                pass
                            else:
                                self.data[self.parameter[col]].append(cell)
                            #print("parameter["+str(col)+"] : "+self.parameter[col]+" : "+str(self.data[self.parameter[col]]))
                            col+=1
                        self.data_row += 1
            else:
                pass

    def save_to_db(self,db):
        db_parameter = []
        datas = []
        trigger = 0
        
        os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
        # <----- read first row parameter ----->
        with open(db,'r') as opf:
            for rw in opf:
                cells = rw.split(",")
                cells[-1] = cells[-1].rstrip("\n")
                if trigger == 0:
                    for cell in cells:
                        db_parameter.append(cell)
                    trigger = 1
                else:
                    #<----- read row[1:] ---->
                    datas.append([])
                    for cell in cells:
                        datas[-1].append(cell)

        # <----- append data accordingly ----->
        processed_data = []
        # <----- append back previous data --->
        processed_data.append([])
        for k,para in enumerate(db_parameter): #first row is parameter 
            processed_data[-1].append(para)
        for k,rw in enumerate(datas): #others row is data 
            processed_data.append([])
            for cell in rw:
                processed_data[-1].append(cell)
        current_len = len(processed_data)
        
        #print(self.data)
        # <---- writing new data ---->
        for rw in range(self.data_row):
            write_counter = 0
            processed_data.append([])
            for para in db_parameter:
                if para in self.parameter:
                    if "Sample Name" in para:
                        l = list(self.data[para][rw])
                        l[6] = '_'
                        self.data[para][rw] = "".join(l)  # replace position 6 "_" to be "_", just to make sure
                    processed_data[-1].append(self.data[para][rw])
                    write_counter += 1
                else:
                    processed_data[-1].append("0")
        try:
            # <---- auto append new parameter --->
            if write_counter == self.data_col: 
                for para in self.data:
                    if para in db_parameter:
                        pass
                    else:
                        # found new parameter
                        processed_data[0].append(para) # add the new paramter into first row
                        for k,processed_row in enumerate(processed_data[:current_len]):
                            if k>0:
                                processed_data[k].append("0") # add zero to previous row
                        for k,processed_row in enumerate(processed_data[current_len:]):
                            processed_data[k+current_len].append(self.data[para][k])
            

            os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
            # <---- write processed datas into database.csv ---->
            with open("data_base.csv",'w') as opf:
                for row in processed_data:
                    for k,cell in enumerate(row):
                        if len(row)-k==1: # last cell of the row
                            opf.write(cell+"\n")
                        else:
                            opf.write(cell+",")
        except Exception:
            print("This file ... i dont know")

def id_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def security_check(request):
    passport = request.GET.get("passport")
    if read_hash(passport) == False:
        os.chdir(settings.BASE_ROOT)
        print("redirect to unautorized")
        return False
    else:
        print("redirect to Autorized")
        return passport

def index(request):
    # initialization
    return render(request,'index.html')


def home(request):
    # login 
    os.chdir(settings.BASE_ROOT)
    return render(request,'home.html',{"result":""})

def console(request):
    # landing page
    passport = security_check(request)
    if passport == False:
        return render(request,'unauthorized.html')
    else:
        return render(request,'console.html',{"passport":passport})

def register(request):
    bad_chars = [';', ':', '!', "*", "(", ")", ",", ".", "&", "#", "^"]
    # landing page
    code = request.POST.get("code")
    ic = request.POST.get("r_ic")
    password = request.POST.get("r_password")
    site = request.POST.get("site")
    bad_trig = 0


    for bad_char in bad_chars:
        if bad_char in code:
            result = "Registration unsuccesfull, Forbidden Character ' " + bad_char + " 'in Activation Code."
            bad_trig = 1
            break
        elif bad_char in ic:
            result = "Registration unsuccesfull, Forbidden Character ' " + bad_char + " ' in User Name."
            bad_trig = 1
            break
        elif bad_char in password:
            result = "Registration unsuccesfull, Forbidden Character ' " + bad_char + " ' in Password."
            bad_trig = 1
            break
        elif " " in ic:
            result = "Registration unsuccesfull, Forbidden Character 'Empty Space' in User Name."
            bad_trig = 1
            break
        elif " " in password:
            result = "Registration unsuccesfull, Forbidden Character 'Empty Space' in Password."
            bad_trig = 1
            break
        else:
            pass
    if bad_trig == 0: #can trigger
        os.chdir(settings.MEDIA_ROOT)
        reg_trig = 0
        uname_list = []
        with open('uname.csv','r') as opf:
            for rw in opf:
                uname_list.append([])
                cells = rw.split(",")
                if ic == cells[0]:
                    reg_trig = 3 #duplicated ic
                    break
                if len(cells)>1:
                    for cell in cells:
                        uname_list[-1].append(cell)
                else:
                    r_code = cells[0].rstrip("\n")
                    #print("'"+code+"' versus. '"+r_code+"'")
                    if code == r_code:
                        uname_list[-1].append(ic)
                        uname_list[-1].append(password)
                        uname_list[-1].append("Newly Registered")
                        uname_list[-1].append(str(datetime.datetime.now()))
                        uname_list[-1].append(site+"\n")
                        reg_trig = 1
                    else:
                        uname_list[-1].append(cells[0])

                        
        if reg_trig == 1:
            with open('uname.csv','w') as opf:
                for rw in uname_list:
                    for cell in rw:
                        opf.write(cell)
                        if "\n" in cell:
                            pass
                        else:
                            opf.write(",")

            result = "Succesfully Registered, User Name is '"+ic+"'"
        elif reg_trig == 3:
            result = "Register Unsuccesfully, User Name '"+ic+"' found previously registered."
        else:
            result = "Register Unsuccesfully, Activation Code not found."



        os.chdir(settings.BASE_ROOT)


    return render(request,'home.html',{"result":result})

def sorting(save_list):
    r_list = []
    sorted_list = []
    for rw in save_list:
        site = rw.split(",")[0]
        samplename = rw.split(",")[1]
        samplename = samplename.replace("-","_")
        date_str = samplename.split("_")[0]
        date = float(re.sub('[^0-9]+', '', date_str))
        sample = samplename.split("_")[1]
        #print("opening list"+str(date))
        r_list.append([site,date,sample,rw])
    #start sort
    #print("starting to sort"+str(r_list))

    r_list.sort()
    #print("sort completed !")
    return r_list

def remove(request):
    # landing page
    passport = security_check(request)
    if passport == False:
        return render(request,'unauthorized.html')
    else:
        if request.method == 'POST':
            print("redirect to Autorized")
            # <------ capture POST parameters ------>
            site = request.POST.get("site")
            date1 = request.POST.get("date1")
            date2 = request.POST.get("date1")
            parameter1 = request.POST.get("parameter1")
            parameter2 = request.POST.get("parameter2")
            parameter3 = request.POST.get("parameter3")
            sample1 = request.POST.get("sample1")
            sample2 = request.POST.get("sample2")
            sample3 = request.POST.get("sample3")
            #print(sample1)

            if date1=="":
                date1="0000-00-00"
                date2=date1
            #if date2=="":
            #    date2="9999-99-99"
            #if parameter1=="":
            parameter1="All"

            sample = [sample1,sample2,sample3]
            parameter = [parameter1,parameter2,parameter3]
            
            os.chdir(settings.MEDIA_ROOT)
            result = process_table("data_base.csv")
            p_result = process_result(result,"avg")

            raw_result = [[[],[]]]
            with open("data_base.csv", 'r') as opf:
                raw_trig = 0
                for rw in opf:
                    if raw_trig == 1:
                        raw_result[0][1].append([])
                    for cell in rw.split(","):
                        if raw_trig == 0:
                            raw_result[0][0].append(cell)
                        else:
                            raw_result[0][1][-1].append(cell)
                    raw_trig = 1
                    

            file_len = len(result[0][0])
            data_len = len(result[0][1])
            remove_indicator = 0
            remove_list = []
            if data_len>1:
                #<----- remove in progress ---->
                with open("data_base.csv", 'w') as opf:
                    # must write back the header of table
                    row_len = len(raw_result[0][0])
                    for k,cell in enumerate(raw_result[0][0]):
                        if "Date" in cell or "Trial" in cell:
                            pass
                        else:
                            opf.write(cell)
                            if row_len-k==1:
                                pass
                            else:
                                opf.write(",")
                    for k,rw in enumerate(raw_result[0][1]):
                        #[Site,Sample Name,Description,OC,VM_1,Moisture,NOS,Oil Content,Moisture_1,FFA]
                        remove_trig = 0
                        sample_rw = rw[1].split("_")
                        r_date = sample_rw[0]
                        date = "20"+r_date[:2]+"-"+r_date[2:4]+"-"+r_date[4:]
                        s_site = rw[0]
                        if date == date1:
                            if site =="All" or site == s_site:
                                for i, data in enumerate(rw):
                                    if sample1 == "All" or sample_rw[1] == sample1:
                                        if i ==0:
                                            #print("Removed : "+str(rw))
                                            remove_site = rw[0]
                                            remove_file_name = rw[1].split("_")[0]+"_"+rw[1].split("_")[1]+".csv"
                                            remove_list.append([remove_site,remove_file_name])
                                            remove_trig = 1
                                            remove_indicator += 1
                        #else:
                        #    print(date1 + " < " + date + " < " + date2 +" : False")
                        if remove_trig == 0:
                            for j,cell in enumerate(raw_result[0][1][k]):
                                row_len = len(raw_result[0][1][k])
                                opf.write(cell)
                                if j==0:
                                    pass
                                    #print("Saved : "+str(raw_result[0][1][k]))
                                if row_len-j==1:
                                    pass
                                else:
                                    opf.write(",")
                                    
            if remove_indicator>0:
                 #<----- sorting data_base.cs --->
                para_list = []
                data_list = []
                data_counter = 0
                with open("data_base.csv", 'r') as opf:
                    for rw in opf:
                        if data_counter>0:
                            data_list.append(rw)
                        else:
                            para_list = rw
                        data_counter += 1
                data_list = sorting(data_list)
                #print("printing data now :")
                with open("data_base.csv", 'w') as opf:
                    for para in para_list:
                        opf.write(para)
                    for data in data_list:
                        opf.write(data[3])
                #print("SORTING COMPLETED !")
                
                #<----- remove records.csv ---->
                save_list = []
                with open(settings.MEDIA_ROOT+"/records.csv","r") as opf:
                    for rw in opf:
                        remove_trig = 0
                        cells = rw.split(",")
                        if len(cells)>1:
                            s_site = cells[0]
                            s_records = cells[1].rstrip("\n")
                            for rw2 in remove_list:
                                r_site = rw2[0]
                                r_records = rw2[1]
                                if r_site == s_site and r_records == s_records:
                                    #print("s_records "+str(s_records)+" : r_records "+str(r_records)+" removed!")
                                    remove_trig = 1
                                    break
                                else:
                                    pass
                        if remove_trig == 0:
                            #print("s_records "+str(s_records)+" : r_records "+str(r_records)+" saved!")
                            save_list.append(rw)

                with open(settings.MEDIA_ROOT+"/records.csv","w") as opf:
                    for save in save_list:
                        opf.write(save)
                result = str(remove_indicator)+ " datas succesfully removed."
                os.chdir(settings.BASE_ROOT)
                return render(request,'landing.html',{"landing_display":result,"passport":passport})
            else:
                #<----- no data on that particular date to be remove ---->
                os.chdir(settings.BASE_ROOT)
                if date1 != "0000-00-00":
                    result = "No data was found on "+str(date1)+" at "+str(site)+" mill "
                else:
                    result = "Please select proper date."
                return render(request,'landing.html',{"landing_display":result,"passport":passport})

        else:
            #<----- remove landing page ----->
            os.chdir(settings.MEDIA_ROOT)
            result = process_table("data_base.csv")
            p_result = process_result(result,"avg")
            sample = []

            #find the site
            with open('uname.csv','r') as opf:
                for rw in opf:
                    if len(rw.split(","))>2:
                        p_passport = rw.split(",")[2]
                        if passport == p_passport:
                            sites = rw.split(",")[4]
                            sites = sites.rstrip("\n")
            
            if sites=="Admin":
                sites = ["All","ABM-Apas Balung Mill","KNM-Kunak Mill","LMM-Lumadan Mill","LKM-Langkon Mill","SPGM-Sepagaya Mill","SDM-Sandau Mill","SBRM-Sebrang Mill","SRDM-Kunak Refinery"]

            else:
                sites = [sites]

            try:
                for row in p_result[0][1]:
                    if row[2] in sample:
                        pass
                    else:
                        sample.append(row[2])
                sample.sort()

            except Exception:
                sample = ["No sample found"]

            os.chdir(settings.BASE_ROOT)
            return render(request,'erase_land.html',{"sites":sites,"sample":sample,"passport":passport})

        

def graph(request):
    # graph
    passport = security_check(request)
    if passport == False:
        return render(request,'unauthorized.html')
    else:
        return render(request,'graph.html',{"passport":passport})

def get_log_data():
    data = []
    with open(settings.MEDIA_ROOT+"/uname.csv",'r') as opf:
        for rw in opf:
            data.append([])
            for cell in rw.split(","):
                data[-1].append(cell.rstrip())
    return data

def write_hash(user_data):
    with open(settings.MEDIA_ROOT+"/uname.csv","w") as opf:
        for row in user_data:
            if len(row)>2:
                for k, cell in enumerate(row):
                    cell = cell.rstrip("\n")
                    if k<4:
                        opf.write(cell)
                        opf.write(",")
                    elif k<5:
                        opf.write(cell)
                        opf.write("\n")
                    else:
                        break
            else:
                opf.write(row[0])
                opf.write("\n")

def read_datetime(record_datetime):
    r_date = record_datetime.split(" ")[0]
    year = int(r_date.split("-")[0])
    month = int(r_date.split("-")[1])
    day = int(r_date.split("-")[2])
    r_time = record_datetime.split(" ")[1]
    hour = float(r_time.split(":")[0])
    minute = float(r_time.split(":")[1])
    second = float(r_time.split(":")[2])
    timestamp = (hour*60+minute)*60+second

    return [year,month,day,timestamp]

def read_hash(passport):
    hash_flag = 0
    record_row = []
    k = 0

    with open(settings.MEDIA_ROOT+"/uname.csv","r") as opf:
        for row in opf:
            record_row.append(row)
            if len(row.split(","))>2:
                if passport == row.split(",")[2]:
                    record_datetime = read_datetime(row.split(",")[3])
                    current_datetime = read_datetime(str(datetime.datetime.now()))
                    datetime_flag = 0
                    #<----- make sure same date ----->
                    for i in range(3):
                        if record_datetime[i] != current_datetime[i]:
                            datetime_flag == 1
                    if datetime_flag == 1:
                        return False
                    #<----- compare time -------->
                    elif abs(record_datetime[3]-current_datetime[3])>300:
                        return False
                    else:
                        hash_flag = 1
                        user_row = k
            k+=1
    # <------ update datetime ------>
    if hash_flag == 1:
        with open(settings.MEDIA_ROOT+"/uname.csv","w") as opf:
            for k,rw in enumerate(record_row):
                if k == user_row:
                    cells = rw.split(",")
                    for j, cell in enumerate(cells):
                        if j == 3:
                            opf.write(str(datetime.datetime.now()))
                        else:
                            opf.write(cell)
                        if "\n" in cell:
                            pass
                        else:
                            opf.write(",")
                else:
                    opf.write(rw)
        #print("updated time")
        return True
    else:
        return False

def validity_check(request,passport):
    if read_hash(passport) == False:
        return render(request,'unauthorized.html')
        print("redirect to unautorized")
    else:
        print("redirect to Autorized")

def login(request):
    passport = id_generator(32) # 32 words Hash
    #print(passport)
    uname = request.POST.get("ic")
    passw = request.POST.get("password")
    login_state = 0 # 0 = username not found, 1 = wrong password, 2 = pass

    #<---- read all user data --->
    log_data = get_log_data()
    #print(log_data)

    #<---- compare for login --->
    for k,data in enumerate(log_data):
        if uname == data[0]:
            if passw == data[1]:
                login_state =  2
                log_data[k][2] = passport
                log_data[k][3] = str(datetime.datetime.now())
                break
            else:
                login_state = 1

    if login_state == 2:
        #login success
        write_hash(log_data)
        return render(request,'console.html',{"passport":passport})

    elif login_state==1:
        return render(request,'home.html',{"result":"Incorrect Password."})
    
    else:
        return render(request,'home.html',{"result":"Username not found."})

def zerolistmaker(n):
    listofzeros = [0] * n
    return listofzeros

def add_parameter(parameter):
    old_data = []
    rw_flag = 0
    with open('data_base.csv', 'r') as opf:  
        for rw in opf:
            old_data.append([])
            for cell in rw.split(","):
                if rw_flag == 0:
                    if "\n" in cell:
                        old_data[-1].append(cell[:-1])
                        old_data[-1].append(parameter+"\n")
                    else:
                        old_data[-1].append(cell)
                else:
                    if "\n" in cell:
                        old_data[-1].append(cell[:-1])
                        old_data[-1].append("0\n")
                    else:
                        old_data[-1].append(cell)
            rw_flag = 1
    
    for k,rw in enumerate(old_data):
        for j,cell in enumerate(rw):
            if cell =="":
                del old_data[k][j]
    
    rw_len = len(old_data[0])
    with open('data_base_test.csv', 'w') as opf:  
        for rw in old_data[:-1]:
            for k in range(rw_len):
                opf.write(rw[k])
                if rw_len-k==1:
                    pass
                else:
                    opf.write(",")

def db_sort():
    #<----- sorting data_base.cs --->
    para_list = []
    data_list = []
    data_counter = 0
    with open(settings.MEDIA_ROOT+"/data_base.csv", 'r') as opf:
        for rw in opf:
            if data_counter>0:
                data_list.append(rw)
            else:
                para_list = rw
            data_counter += 1

    data_list = sorting(data_list)

    if len(data_list)>2:
        #print("printing data now :")
        with open(settings.MEDIA_ROOT+"/data_base.csv", 'w') as opf:
            for para in para_list:
                opf.write(para)
            for data in data_list:
                opf.write(data[3])
        #print("SORTING COMPLETED !")

def post_process_upload(site):
    #<----- post process all sub csv into main csv file ---->
    os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
    mypath = settings.MEDIA_ROOT
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))] # get file names within zip file
    datas = []

    # <------ Read all data from processed csv----->
    for fil in onlyfiles:
        if "uname.csv" == fil:
            pass
            
        elif "data_base.csv" == fil:
            pass
        
        elif "records.csv" == fil:
            pass
            
        elif ".csv" in fil:
            with open(settings.MEDIA_ROOT+"/"+fil, 'r') as opf:  
                #print("readed : "+settings.MEDIA_ROOT+"/"+fil)
                datas.append(parameter(opf,site))
            with open("records.csv","a") as opf:
                opf.write(site+","+fil+"\n")
            os.remove(settings.MEDIA_ROOT+"/"+fil) # move file to history records

        else:
            pass
            

    os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
    for data in datas:
        data.save_to_db('data_base.csv')

    db_sort()

    os.chdir(settings.BASE_ROOT) #cd back to base directory

def process_upload_file(fil,directory):
    if "~$" in fil:
        print("I mean rejected :D") 
    elif ".xlsx" in fil:
        os.chdir(directory) #write the exceldata into csv in media dir
        #print("found "+fil+"!\n")
        filename = fil[:-5]
        try:
            wb = openpyxl.load_workbook(directory+'/'+filename+'.xlsx')
            sh = wb.get_active_sheet()
            os.remove(fil)
            os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
            with open(filename+'.csv', 'w', newline="") as f:  # open('test.csv', 'w', newline="") for python 3
                c = csv.writer(f)
                for r in sh.rows:
                    c.writerow([cell.value for cell in r])
        except Exception:
            print("bad boy : "+str(filename))
            os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
    elif ".csv" in fil:
        os.chdir(directory) #write the exceldata into csv in media dir
        #print("found "+fil+"!\n")
        filename = fil[:-4]
        try:
            rec_datas = []
            with open(filename+'.csv','r') as opf:
                for rw in opf:
                    rec_datas.append(rw)
            os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
            with open(filename+'.csv', 'w') as opf:  # open('test.csv', 'w', newline="") for python 3
                for rec in rec_datas:
                    opf.write(rec)
        except Exception:
            print("bad boy : "+str(filename))
            os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
    else:
        #os.remove(fil) 
        pass

def upload_file(request):
    passport = security_check(request)
    if passport == False:
        return render(request,'unauthorized.html')
    else:
        if request.method == 'POST':
            # <------ Process upload 'POST' request ----->
            try:
                site = request.POST.get("site")
                up_file = request.FILES['document']
                fs = FileSystemStorage()
                fs.save(up_file.name, up_file)
                sucess_flag = 0
                duplicated_counter = 0
                if ".zip" in up_file.name:
                    # <------ Zip file extraction ----->
                    os.chdir(settings.MEDIA_ROOT)
                    patoolib.extract_archive(up_file.name,outdir="unpack")

                    # <------ Conver all extracted file from.xlsx to .csv  ----->
                    folders = []
                    # r=root, d=directories, f = files
                    for r, d, f in os.walk(settings.MEDIA_ROOT):
                        for folder in d:
                            folders.append(os.path.join(r, folder)) #get all folders within the zip
                    for folder in folders:
                        if "records" in folder:
                            pass
                        else:
                            os.chdir(folder) # cd to all directories within the zip file
                            mypath = folder
                            onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))] # get file names within zip file
                            for fil in onlyfiles:
                                remove_trig = 0 
                                prevent_files_list = []
                                with open(settings.MEDIA_ROOT+"/records.csv", 'r') as opf:
                                    for rw in opf:
                                        cells = rw.split(",")
                                        prevent_files_list.append([cells[0],cells[1].rstrip(".csv\n")])
                                file_name = fil.rstrip(".xlsx")
                                file_name = file_name.rstrip(".csv")
                                for rw in prevent_files_list:
                                    prevent_site = rw[0]
                                    prevent_file = rw[1]
                                    if file_name in prevent_file and site == prevent_site:
                                        print("file name = "+str(file_name)+" : prevent_file = "+str(prevent_file)+" Duplicated")
                                        last_dir = os.getcwd()
                                        os.chdir(folder)
                                        os.remove(fil) 
                                        os.chdir(last_dir)
                                        duplicated_counter+=1
                                        duplicated_filname = fil
                                        remove_trig = 1
                                        break
                                if remove_trig == 0:
                                    print("file name = "+str(file_name)+" Went to Saving process ")
                                    process_upload_file(fil,folder)
                                        
                    os.chdir(settings.MEDIA_ROOT)
                    os.remove(up_file.name)
                    result = "Succesfully uploaded " + up_file.name
                    if duplicated_counter>0:
                        if duplicated_counter == 1:
                            result += ", but "+duplicated_filname+" for "+site+" mill was found duplicated."
                        else:
                            result += ", but "+str(duplicated_counter)+" files for "+site+" mill was found duplicated."
                    os.chdir(settings.BASE_ROOT)
                    sucess_flag = 1

                    # <------ Delete all unzip directories  ----->
                    for folder in folders:
                        try:
                            if "records" in folder:
                                pass
                            else:
                                shutil.rmtree(folder) 
                        except Exception:
                            print("no such directory "+folder)

                elif ".xlsx" in up_file.name:
                    # <------ Convert .xlsx to .csv----->
                    remove_trig = 0
                    duplicated_counter = 0
                    prevent_files_list = []
                    fil = up_file.name
                    with open(settings.MEDIA_ROOT+"/records.csv", 'r') as opf:
                        for rw in opf:
                            cells = rw.split(",")
                            prevent_files_list.append([cells[0],cells[1].rstrip(".csv\n")])
                    file_name = fil.rstrip(".xlsx")
                    for rw in prevent_files_list:
                        prevent_site = rw[0]
                        prevent_file = rw[1]
                        if file_name in prevent_file and site == prevent_site:
                            print("Duplicated : "+fil)
                            os.chdir(settings.MEDIA_ROOT)
                            os.remove(up_file.name) 
                            os.chdir(settings.BASE_ROOT)
                            duplicated_counter+=1
                            duplicated_filname = fil
                            remove_trig = 1
                            break
                    if remove_trig == 0:
                        process_upload_file(up_file.name,settings.MEDIA_ROOT)
                    result = "Succesfully uploaded " + up_file.name
                    if duplicated_counter>0:
                        result = "Unsuccessful upload, because "+fil+" for "+site+" mill was found duplicated."
                    sucess_flag = 1

                elif ".csv" in up_file.name:
                    # <------ Convert .xlsx to .csv----->
                    remove_trig = 0
                    duplicated_counter = 0
                    prevent_files_list = []
                    fil = up_file.name
                    with open(settings.MEDIA_ROOT+"/records.csv", 'r') as opf:
                        for rw in opf:
                            cells = rw.split(",")
                            prevent_files_list.append([cells[0],cells[1].rstrip(".csv\n")])
                    file_name = fil.rstrip(".csv")
                    for rw in prevent_files_list:
                        prevent_site = rw[0]
                        prevent_file = rw[1]
                        if file_name in prevent_file and site == prevent_site:
                            print("Duplicated : "+fil)
                            os.chdir(settings.MEDIA_ROOT)
                            os.remove(up_file.name) 
                            os.chdir(settings.BASE_ROOT)
                            duplicated_counter+=1
                            duplicated_filname = fil
                            remove_trig = 1
                            break
                    if remove_trig == 0:
                        process_upload_file(up_file.name,settings.MEDIA_ROOT)
                    result = "Succesfully uploaded " + up_file.name
                    if duplicated_counter>0:
                        result = "Unsuccessful upload, because "+fil +" for "+site+" mill was found duplicated."
                    sucess_flag = 1

                else:
                    # <------ Delete unrecognized file----->
                    os.chdir(settings.MEDIA_ROOT) #write the exceldata into csv in media dir
                    os.remove(up_file.name) 
                    result = "Error : Unrecognized file type. \n(Make sure only .zip .xlsx or .csv are uploaded)"
                    os.chdir(settings.BASE_ROOT) #write the exceldata into csv in media dir
                    sucess_flag = 0

                if sucess_flag == 1:
                    post_process_upload(site)
                    db_sort()

                #find the site
                os.chdir(settings.MEDIA_ROOT)
                with open('uname.csv','r') as opf:
                    for rw in opf:
                        if len(rw.split(","))>2:
                            p_passport = rw.split(",")[2]
                            if passport == p_passport:
                                sites = rw.split(",")[4]
                                sites = sites.rstrip("\n")

                if sites=="Admin":
                    sites = ["ABM-Apas Balung Mill","KNM-Kunak Mill","LMM-Lumadan Mill","LKM-Langkon Mill","SPGM-Sepagaya Mill","SDM-Sandau Mill","SBRM-Sebrang Mill","SRDM-Kunak Refinery"]

                else:
                    sites = [sites]
                os.chdir(settings.BASE_ROOT) 
            
            
            except Exception:
                #find the site
                os.chdir(settings.MEDIA_ROOT)
                with open('uname.csv','r') as opf:
                    for rw in opf:
                        if len(rw.split(","))>2:
                            p_passport = rw.split(",")[2]
                            if passport == p_passport:
                                sites = rw.split(",")[4]
                                sites = sites.rstrip("\n")

                if sites=="Admin":
                    sites = ["ABM-Apas Balung Mill","KNM-Kunak Mill","LMM-Lumadan Mill","LKM-Langkon Mill","SPGM-Sepagaya Mill","SDM-Sandau Mill","SBRM-Sebrang Mill","SRDM-Kunak Refinery"]

                else:
                    sites = [sites]
                result = "Please select a file to upload"

        else:
            os.chdir(settings.MEDIA_ROOT)
            #find the site
            with open('uname.csv','r') as opf:
                for rw in opf:
                    if len(rw.split(","))>2:
                        p_passport = rw.split(",")[2]
                        if passport == p_passport:
                            sites = rw.split(",")[4]
                            sites = sites.rstrip("\n")

            if sites=="Admin":
                sites = ["ABM-Apas Balung Mill","KNM-Kunak Mill","LMM-Lumadan Mill","LKM-Langkon Mill","SPGM-Sepagaya Mill","SDM-Sandau Mill","SBRM-Sebrang Mill","SRDM-Kunak Refinery"]

            else:
                sites = [sites]
            os.chdir(settings.BASE_ROOT) 

            result = ""

        os.chdir(settings.BASE_ROOT) #write the exceldata into csv in media dir
        return render(request, 'upload.html',{"sites":sites,"result":result,"passport":passport}) 

def process_table(fil):
    # show data
    result = []
    result.append([])
    with open(fil) as opf:
        parameter = []
        data = []
        dflag = 0
        for row in opf:
            cells = row.split(",")
            if dflag == 1:
                data.append([])
                for cell in cells:
                    data[-1].append(cell) #record all data
            elif cells[0]=="Site":
                for cell in cells:
                    parameter.append(cell) #record all parameter
                dflag=1
            else:
                pass
        result[-1].append([]) # [0] is parameter
        result[-1].append([]) # [1] is data
        # remove all empty cell
        if len(data) == 0:
            for para in parameter:
                result[-1][0].append(para)
            result[-1][1].append([])
        else:
            for j,row in enumerate(data):
                result[-1][1].append([])
                for i,cell in enumerate(row):
                    if cell == "" or cell=="\n":
                        pass
                    else:
                        if j==0:
                            result[-1][0].append(parameter[i])
                        result[-1][1][-1].append(cell)
    return result

def remove_bad_chars(inp):
    bad_chars = [';', ':', '!', "*", "(", ")", "-", "_"]
    
    for i in bad_chars : 
        inp = inp.replace(i, '') 
    return inp

def process_result(result,mode): # mode = avg, min and max
    p_result = [[]] # processed result list
    result[0][0][-1] = result[0][0][-1].rstrip("\n")
    if len(result[0][1]) == 1:
        p_result[0].append(result[0][0])
        p_result[0].append([])
        p_result[0][1].append([])

        return p_result
    else:
        #<----- process header ------>
        #['Site', 'Sample Name', 'Description', 'OC', 'VM_1', 'Moisture', 'NOS', 'Oil Content', 'Moisture_1', 'FFA']
        result[0][0].insert(1,"Date")
        #result[0][0].insert(3,"Trial")
        p_result[0].append(result[0][0])
        p_result[0].append([])
        #print(p_result[0][0]) # debug

        #<----- process data ------>
        last_trial = -1
        last_name = "last_name_init"
        sum_avg = []
        avg=[]
        avg_counter = 1
        maximal = 99999999.99
        minimal = -9999999999.99
        max_list = []
        min_list = []
        maxmin_flag = 0
        #print(mode)
        for p,res in enumerate(result[0][1]):
            res[-1] = res[-1].rstrip("\n")
            res[1] = res[1].replace("-","_")
            #['Beufort', '190408_SC_03_(01)', 'HAMSAH LAHAMID', '0', '0', '94.9676367295357', '4.08136453094159', '1.21644933837748', '0', '0']
            undate = res[1].split("_")[0]
            date = "20"+undate[:2]+"-"+undate[2:4]+"-"+undate[4:]
            sample = res[1].split("_")[1]
            #trial = res[1].split("_")[2]
            
            sample = remove_bad_chars(sample)
            #trial = remove_bad_chars(trial)
            try:
                res_buffer = result[0][1][p+1][1].replace("-", '_') 
                next_name = res_buffer.split("_")[1]
                undate = res_buffer.split("_")[0]
                next_date = "20"+undate[:2]+"-"+undate[2:4]+"-"+undate[4:]
                #next_trial = result[0][1][p+1][1].split("_")[2]
                next_name = remove_bad_chars(next_name)
                #next_trial = remove_bad_chars(next_trial)
            except Exception:
                next_name = "End of file"
                next_date = "End of file"
                #next_trial = -1
            del res[1]
            res.insert(1,date)
            res.insert(2,sample)
            #res.insert(3,trial)

            # <------ Calculation part ----->
            if mode == "avg":
                # same parameter and trial
                if date == next_date and next_name == sample:
                    sum_avg.append(res[5:])
                    avg_counter += 1
                else:
                    trig = 0
                    sum_avg.append(res[5:])
                    for k,row in enumerate(sum_avg):
                        trig = 1
                        for i,cell in enumerate(row):
                            if k == 0:
                                avg.append(float(cell))
                            else:
                                avg[i]+=float(cell)
                    if trig == 0:
                        avg = res[5:]
                    else:
                        for k,av in enumerate(avg):
                            avg[k] = str(av/avg_counter)
                    res[5:]=avg
                    p_result[0][1].append(res)
                    sum_avg = []
                    avg=[]
                    avg_counter = 1

            elif mode == "max":
                # same parameter and trial
                if date == next_date and next_name == sample:
                    for k,cell in enumerate(res[5:]):
                        if maxmin_flag == 0:
                            max_list.append(float(cell))
                        else:
                            if max_list[k]<float(cell):
                                max_list[k] = float(cell)
                    maxmin_flag = 1
                else:
                    if maxmin_flag == 1:
                        for k,cell in enumerate(res[5:]):
                            if max_list[k]<float(cell):
                                max_list[k] = float(cell)
                        res[5:]=max_list
                    p_result[0][1].append(res)
                    max_list = []
                    maxmin_flag=0
                
            elif mode == "min":
                # same parameter and trial
                if date == next_date and next_name == sample:
                    for k,cell in enumerate(res[5:]):
                        if maxmin_flag == 0:
                            min_list.append(float(cell))
                        else:
                            if min_list[k]>float(cell):
                                min_list[k] = float(cell)
                    maxmin_flag = 1
                else:
                    if maxmin_flag == 1:
                        for k,cell in enumerate(res[5:]):
                            if min_list[k]>float(cell):
                                min_list[k] = float(cell)
                        res[5:]=min_list
                    p_result[0][1].append(res)
                    min_list = []
                    maxmin_flag=0

            else: # don know... if fall in this loop, the last value will be taken :O
                # same parameter and trial
                if date == next_date and next_name == sample:
                    for k,cell in enumerate(res[5:]):
                        if p == 0:
                            min_list.append(float(cell))
                        else:
                            min_list[k] = float(cell)
                else:
                    res[5:]=min_list
                    p_result[0][1].append(res)
                
            #print(p_result[0][1][-1]) #debug
            #<---- save last memory ---->
            last_name = sample
    return p_result

def check_date_statemachine(inp1,inp,inp2,state):
    #state: 0 = True, finish  
    #     : 1 = compare inp1 and inp, need process next (year > month > date)
    #     : 2 = compare inp and inp2, need process next (year > month > date)
    #     : 3 = compare both inp1 and inp2, need process next (year > month > date)
    #     : 4 = False, finish

    if inp1<inp and inp<inp2:
        state = 0
    if state == 3:
        if inp1==inp and inp<inp2:
            state = 1
        elif inp1<inp and inp==inp2:
            state = 2
        elif inp1==inp and inp==inp2:
            state = 3
        else:
            state = 4
    elif state == 1:
        if inp1<inp:
            state = 0
        elif inp1==inp:
            state = 1
        else:
            state = 4
    elif state == 2:
        if inp<inp2:
            state = 0
        elif inp==inp2:
            state = 2
        else:
            state = 4
    else:
        state = -1
    return state

def check_datetime(date1,date,date2):
    dates=[date1,date,date2]
    year = []
    month = []
    day = []
    for d in dates:
        year.append(int(d.split("-")[0]))
        month.append(int(d.split("-")[1]))
        day.append(int(d.split("-")[2]))
    
    state = check_date_statemachine(year[0],year[1],year[2],3)
    if state == 0:
        return True
    elif state == 4:
        return False 
    else:
        state = check_date_statemachine(month[0],month[1],month[2],state)
        if state == 0:
            return True
        elif state == 4:
            return False 
        else:
            state = check_date_statemachine(day[0],day[1],day[2],state)
            if state == 0:
                return True
            elif state == 4:
                return False 
            else:
                return True

def tabulate(request):
    # show data
    passport = security_check(request)
    if passport == False:
        return render(request,'unauthorized.html')
    else:
        if request.method == 'POST':
            print("redirect to Autorized")
            # <------ capture POST parameters ------>
            site = request.POST.get("site")
            date1 = request.POST.get("date1")
            date2 = request.POST.get("date2")
            parameter1 = request.POST.get("parameter1")
            parameter2 = request.POST.get("parameter2")
            parameter3 = request.POST.get("parameter3")
            sample1 = request.POST.get("sample1")
            sample2 = request.POST.get("sample2")
            sample3 = request.POST.get("sample3")

            if date1=="":
                date1="0000-00-00"
            if date2=="":
                date2="9999-99-99"
            #if parameter1=="":
            parameter1="All"
            sample = [sample1,sample2,sample3]
            parameter = [parameter1,parameter2,parameter3]
            all_input = [site,date1,date2,parameter1,parameter2,parameter3,sample1,sample2,sample3]

            # <------ debuging purpose ------>
            #print(site)
            #print(date1)
            #print(date2)
            #print(parameter1)
            #print(parameter2)
            #print(parameter3)
            #print(sample)

            db_sort()
            mypath = settings.MEDIA_ROOT
            os.chdir(settings.MEDIA_ROOT)
            onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))] # get file names within zip file
            s_result = [[[],[]]]
            for fil in onlyfiles:
                if "data_base.csv" in fil: #just to be sure it is database csv
                    result = process_table(fil)
                    p_result = process_result(result,"avg")
                    #['Site', 'Date', Sample Name', 'Trial', 'Description', 'OC', 'VM_1', 'Moisture', 'NOS', 'Oil Content', 'Moisture_1', 'FFA']

                    # <----- append header ----->
                    take_list = [] # which column need to take
                    for k,para in enumerate(p_result[0][0]):
                        if parameter1 == "All":
                            s_result[0][0].append(para)
                            take_list.append(k)
                        else:
                            if k < 5 or para in parameter:
                                s_result[0][0].append(para)
                                take_list.append(k)

                    # <----- append data ----->
                    if len(p_result[0][1]) == 1:
                        s_result[0][1].append([])
                    else:
                        for row in p_result[0][1]:
                            date = row[1]
                            s_site = row[0]
                            if check_datetime(date1,date,date2) == True:
                                if site =="All" or site == s_site:
                                    s_result[0][1].append([])
                                    for k,data in enumerate(row):
                                        if k in take_list:
                                            if sample[0] == "All" or row[2] in sample:
                                                if k>=5:
                                                    s_result[0][1][-1].append(str(round(float(data),4)))
                                                else:
                                                    s_result[0][1][-1].append(data)
                        
                else:
                    if "uname.csv" in fil or "records.csv" in fil:
                        pass
                    else:
                        os.remove(fil)


            os.chdir(settings.BASE_ROOT)
            #print(s_result[0][0])
            #for data in s_result[0][1]:
            #    print(data)
            return render(request,'tabulate.html',{'result':s_result,"t_show":"Data Analytics","all_input":all_input,"passport":passport})
        
        else:
            mode = request.GET.get("set")
            if mode == None:
                try:
                    os.chdir(settings.MEDIA_ROOT)
                    result = process_table("data_base.csv")
                    p_result = process_result(result,"avg")
                    
                    #find the site
                    with open('uname.csv','r') as opf:
                        for rw in opf:
                            if len(rw.split(","))>2:
                                p_passport = rw.split(",")[2]
                                if passport == p_passport:
                                    sites = rw.split(",")[4]
                                    sites = sites.rstrip("\n")

                    if sites=="Admin":
                        sites = ["All","ABM-Apas Balung Mill","KNM-Kunak Mill","LMM-Lumadan Mill","LKM-Langkon Mill","SPGM-Sepagaya Mill","SDM-Sandau Mill","SBRM-Sebrang Mill","SRDM-Kunak Refinery"]

                    else:
                        sites = [sites]

                    parameter = []
                    for para in result[0][0][5:]:
                        parameter.append(para)

                    sample = []
                    for row in p_result[0][1]:
                        if row[2] in sample:
                            pass
                        else:
                            sample.append(row[2])
                    
                    sample.sort()
                except Exception:
                    sample=[]
                    parameter=[]

                os.chdir(settings.BASE_ROOT)
                return render(request,'tabulate_land.html',{"sites":sites,"sample":sample,"parameter":parameter,"passport":passport})

            else:
                #<------- clicked avg, max or min ----------->
                all_input = request.GET.get("all_input")
                #print(all_input)
                site = all_input.split(",")[0]
                date1 = all_input.split(",")[1]
                date2 = all_input.split(",")[2]
                parameter1 = all_input.split(",")[3]
                parameter2 = all_input.split(",")[4]
                parameter3 = all_input.split(",")[5]
                sample1 = all_input.split(",")[6]
                sample2 = all_input.split(",")[7]
                sample3 = all_input.split(",")[8]

                if date1=="":
                    date1="0000-00-00"
                if date2=="":
                    date2="9999-99-99"
                #if parameter1=="":
                parameter1="All"

                sample = [sample1,sample2,sample3]
                parameter = [parameter1,parameter2,parameter3]

                all_input = [site,date1,date2,parameter1,parameter2,parameter3,sample1,sample2,sample3]
                
                os.chdir(settings.MEDIA_ROOT)
                result = process_table("data_base.csv")
                p_result = process_result(result,mode)
                s_result = [[[],[]]]
                #['Site', 'Date', Sample Name', 'Trial', 'Description', 'OC', 'VM_1', 'Moisture', 'NOS', 'Oil Content', 'Moisture_1', 'FFA']

                # <----- append header ----->
                take_list = [] # which column need to take
                for k,para in enumerate(p_result[0][0]):
                    if parameter1 == "All":
                        s_result[0][0].append(para)
                        take_list.append(k)
                    else:
                        if k < 5 or para in parameter:
                            s_result[0][0].append(para)
                            take_list.append(k)

                # <----- append data ----->
                for row in p_result[0][1]:
                    date = row[1]
                    s_site = row[0]
                    if check_datetime(date1,date,date2) == True:
                        if site =="All" or site == s_site:
                            s_result[0][1].append([])
                            for k,data in enumerate(row):
                                if k in take_list:
                                    if sample[0] == "All" or row[2] in sample:
                                        if k>=5:
                                            s_result[0][1][-1].append(str(round(float(data),4)))
                                        else:
                                            s_result[0][1][-1].append(data)
                    
                os.chdir(settings.BASE_ROOT)
                return render(request,'tabulate.html',{'result':s_result,"t_show":"Data Analytics","all_input":all_input,"passport":passport})

def raw(request):
    # show data
    passport = security_check(request)
    if passport == False:
        return render(request,'unauthorized.html')
    else:
        if request.method == 'POST':
            mypath = settings.MEDIA_ROOT
            os.chdir(settings.MEDIA_ROOT)
            onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))] # get file names within zip filesite = request.POST.get("site")
            date1 = request.POST.get("date1")
            date2 = request.POST.get("date2")
            site = request.POST.get("site")
            sample1 = request.POST.get("sample1")
            if date1=="" or date2=="":
                try:
                    os.chdir(settings.MEDIA_ROOT)
                    result = process_table("data_base.csv")
                    p_result = process_result(result,"avg")
                    
                    #find the site
                    with open('uname.csv','r') as opf:
                        for rw in opf:
                            if len(rw.split(","))>2:
                                p_passport = rw.split(",")[2]
                                if passport == p_passport:
                                    sites = rw.split(",")[4]
                                    sites = sites.rstrip("\n")

                    if sites=="Admin":
                        sites = ["All","ABM-Apas Balung Mill","KNM-Kunak Mill","LMM-Lumadan Mill","LKM-Langkon Mill","SPGM-Sepagaya Mill","SDM-Sandau Mill","SBRM-Sebrang Mill","SRDM-Kunak Refinery"]

                    else:
                        sites = [sites]

                    parameter = []
                    for para in result[0][0][5:]:
                        parameter.append(para)

                    sample = []
                    for row in p_result[0][1]:
                        if row[2] in sample:
                            pass
                        else:
                            sample.append(row[2])
                    sample.sort()
                except Exception:
                    sample=[]
                    parameter=[]
                result = "Please select a proper date."

                os.chdir(settings.BASE_ROOT)
                return render(request,'raw_land.html',{"result":result,"sites":sites,"sample":sample,"parameter":parameter,"passport":passport})
            parameter1 = "All"

            db_sort() # sort data base

            #<----- add average minimal and maximal in bottom ----->
            buffer_result = process_table("data_base.csv")
            avg_result = process_result(buffer_result,"avg")
            buffer_result = process_table("data_base.csv")
            max_result = process_result(buffer_result,"max")
            buffer_result = process_table("data_base.csv")
            min_result = process_result(buffer_result,"min")

            #for z,avg in enumerate(avg_result[0][1]):
            #    print("avg = "+str(avg))
            #    print("max = "+str(max_result[0][1][z]))
            #    print("min = "+str(min_result[0][1][z]))


            result = [[[],[]]]
            result[0][0].append(" ")
            result[0][0].append("Sample Type")
            for fil in onlyfiles:
                if "data_base.csv" in fil: #just to be sure it is database csv
                    #result = process_table(fil)
                    raw_result = [[[],[]]]
                    with open("data_base.csv", 'r') as opf:
                        raw_trig = 0
                        for rw in opf:
                            if raw_trig == 1:
                                raw_result[0][1].append([])
                            for cell in rw.split(","):
                                if raw_trig == 0:
                                    raw_result[0][0].append(cell)
                                    result[0][0].append(cell)
                                else:
                                    raw_result[0][1][-1].append(cell)
                            raw_trig = 1
                            
                    # <----- filter raw data according to the date, sample and site ----->
                    file_len = len(raw_result[0][0])
                    data_len = len(raw_result[0][1])
                    if data_len>1:
                        for k,rw in enumerate(raw_result[0][1]):
                            append_trig = 0
                            #[Site,Sample Name,Description,OC,VM_1,Moisture,NOS,Oil Content,Moisture_1,FFA]
                            sample_rw = rw[1].split("_")
                            r_date = sample_rw[0]
                            date = "20"+r_date[:2]+"-"+r_date[2:4]+"-"+r_date[4:]
                            s_site = rw[0]
                            if check_datetime(date1,date,date2) == True:
                                if site =="All" or site == s_site:
                                    for i, data in enumerate(rw):
                                        if sample1 == "All" or sample_rw[1] == sample1:
                                            append_trig=1
                                    if append_trig == 1:
                                        result[0][1].append([])
                                        result[0][1][-1].append(" ")
                                        result[0][1][-1].append(sample_rw[1])
                                        for i, data in enumerate(rw):
                                            if i>=4:
                                                result[0][1][-1].append(str(round(float(data),4)))
                                            else:
                                                result[0][1][-1].append(data)
                        
                        # <----- append the max min and avg ------->
                        all_avg = []
                        all_count = 0
                        all_max = [-9999999.99]
                        all_min = [9999999.99]
                            
                        for avgs in avg_result[0][1]:
                            for avg in avgs:
                                all_avg.append(0)
                                all_max.append(-9999999.99)
                                all_min.append(9999999.99)
                            break

                        # calculation of all avg max and min
                        for k,rw in enumerate(result[0][1]): 
                            if k>0:
                                try:
                                    last_sample = result[0][1][k-1][3].split("_")[1]
                                    last_udate = result[0][1][k-1][3].split("_")[0]
                                    last_date = "20"+last_udate[:2]+"-"+last_udate[2:4]+"-"+last_udate[4:]
                                    for j,rw2 in enumerate(avg_result[0][1]):
                                        if rw2[2] == last_sample and rw2[1] == last_date and (site == rw2[0] or site == "All"):
                                            for i,cell in enumerate(rw2):
                                                if i>4:
                                                    all_avg[i]+= float(cell)
                                            all_count+=1
                                            break

                                    for j,rw2 in enumerate(max_result[0][1]):
                                        if rw2[2] == last_sample and rw2[1] == last_date and (site == rw2[0] or site == "All"):
                                            for i,cell in enumerate(rw2):
                                                if i>4 and all_max[i]<float(cell):
                                                    all_max[i] = float(cell)
                                            break

                                    for j,rw2 in enumerate(min_result[0][1]):
                                        if rw2[2] == last_sample and rw2[1] == last_date and (site == rw2[0] or site == "All"):
                                            for i,cell in enumerate(rw2):
                                                if i>4 and all_min[i]>float(cell):
                                                    all_min[i] = float(cell)
                                            break
                                
                                except Exception:
                                    pass # after insertion
                        total_row = k

                        if all_count>0:
                            t_show = "Raw Data."
                            for k, av in enumerate(all_avg):
                                    all_avg[k]=av/all_count

                            # insertion of all avg max and min
                            result[0][1].insert(total_row+1,["",last_sample,"Average","","",""])
                            for av in all_avg[5:]:
                                result[0][1][total_row+1].append(str(round(float(av),4)))
                                print(result[0][1][-1])
                            result[0][1].insert(total_row+2,["",last_sample,"Maximal","","",""])
                            for av in all_max[5:]:
                                result[0][1][total_row+2].append(str(round(float(av),4)))
                            result[0][1].insert(total_row+3,["",last_sample,"Minimal","","",""])
                            for av in all_min[5:]:
                                result[0][1][total_row+3].append(str(round(float(av),4)))
                        else:
                            t_show = "No raw data was found in selected date!"
                        #for rw in result[0][1]:
                        #    print(rw)

                    #avg_result = 
                    #max_result = process_result(buffer_result,"max")
                    #min_result = process_result(buffer_result,"min")
                    #print(all_avg)
                    #print(all_max)
                    #print(all_min)
                    
                
                    #print("\n\n\n\n\nREMOVE PARA")
                    #<----- remove empty para ----->
                    remove_count = []
                    for x in range(len(result[0][0])):
                        remove_count.append(0)
                    for y in range(len(result[0][1])):
                        #print(result[0][1][y])
                        for x in range(len(result[0][0])):
                            if x>5:
                                #print(float(result[0][1][y][x]))
                                if float(result[0][1][y][x]) == 0:
                                    remove_count[x]+=1
                    s_result = [[[],[]]]
                    stay_list = []
                    data_len = len(result[0][1])
                    for k,count in enumerate(remove_count):
                        if data_len==count:
                            pass
                            #print("count = "+str(count)+", data_len = "+str(data_len))
                        else:
                            stay_list.append(k)

                    for k,para in enumerate(result[0][0]):
                        if k in stay_list:
                            s_result[0][0].append(para)
                    for rw in result[0][1]:
                        s_result[0][1].append([])
                        for k,cell in enumerate(rw):
                            if k in stay_list:
                                s_result[0][1][-1].append(cell)
                    result = s_result
                        

                else:
                    if "uname.csv" in fil or "records.csv" in fil:
                        pass
                    else:
                        os.remove(fil)
            os.chdir(settings.BASE_ROOT)
            return render(request,'raw_data.html',{'result':result,"t_show":t_show,"passport":passport})

        else:
            try:
                os.chdir(settings.MEDIA_ROOT)
                result = process_table("data_base.csv")
                p_result = process_result(result,"avg")
                
                #find the site
                with open('uname.csv','r') as opf:
                    for rw in opf:
                        if len(rw.split(","))>2:
                            p_passport = rw.split(",")[2]
                            if passport == p_passport:
                                sites = rw.split(",")[4]
                                sites = sites.rstrip("\n")

                if sites=="Admin":
                    sites = ["All","ABM-Apas Balung Mill","KNM-Kunak Mill","LMM-Lumadan Mill","LKM-Langkon Mill","SPGM-Sepagaya Mill","SDM-Sandau Mill","SBRM-Sebrang Mill","SRDM-Kunak Refinery"]

                else:
                    sites = [sites]

                parameter = []
                for para in result[0][0][5:]:
                    parameter.append(para)

                sample = []
                for row in p_result[0][1]:
                    if row[2] in sample:
                        pass
                    else:
                        sample.append(row[2])
                sample.sort()
            except Exception:
                sample=[]
                parameter=[]

            os.chdir(settings.BASE_ROOT)
            return render(request,'raw_land.html',{"sites":sites,"sample":sample,"parameter":parameter,"passport":passport})
