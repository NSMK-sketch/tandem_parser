
import jinja2
import xml.etree.ElementTree as ET 
from datetime import datetime







def parser(tag,file_name,programSet,plan,compensationTypeShortTitle):

    with open(file_name+".html", mode="w", encoding='utf-8-sig') as file_writer:
        # Форматирование в строку в формате "ГГГГ-ММ-ДД ЧЧ:ММ:СС"
        current_datetime = datetime.now()
        time = current_datetime.strftime("%Y-%m-%d %H:%M")
        items = []
        for tagen in tag.findall('entrant/row'):
            
            statusCode = tagen.attrib['statusCode']
            benefitSpecialCategory=tagen.attrib.get('benefitSpecialCategory')
            if benefitSpecialCategory is not None:
                benefitSpecialCategory="✓"
            else:
                benefitSpecialCategory=" "
            if statusCode=="7" or statusCode == "8":
                continue
                
            # Get the value from the attribute 'name'
            rank = tagen.find('firstRating').text #номер в рейтинге
            fullFio = tagen.attrib['fullFio'] # ФИО
            fullFio=fullFio.capitalize()
            fullFio=fullFio.title()
            averageEduInstitutionMark= tagen.attrib['averageEduInstitutionMark']# Балл аттестата            
            originalSubmissionWay=tagen.attrib['originalIn']# Сдан ли оргинал
            priority=tagen.attrib['priority']
            averageEduInstitutionMark=averageEduInstitutionMark.replace(',', '.')    
            if originalSubmissionWay=='false':
                originalSubmissionWay='НЕТ'
            else:
                if priority=='1':
                    originalSubmissionWay='ДА'
                else:
                    originalSubmissionWay='ДА'


            
            an_item = dict(rank=rank,fullFio=fullFio,originalSubmissionWay=originalSubmissionWay,averageEduInstitutionMark=averageEduInstitutionMark,benefitSpecialCategory=benefitSpecialCategory)
            items.append(an_item)
        loader = jinja2.FileSystemLoader('templates\\page.htm')
        env = jinja2.Environment(loader=loader)
        template = env.get_template('')
        msg=template.render(items=items,time=time,programSet=programSet,plan=plan,compensationTypeShortTitle=compensationTypeShortTitle)
        
        file_writer.write(msg)


def creatCsv(dirload,filename):
    
    listname=[]

    root_node = ET.parse(filename).getroot() 

    id=1
    for tag in root_node.findall('competition/row'): # выбираем тег из которого берем данные

        programSet = tag.get('programSetPrintTitle')
        compensationTypeShortTitle=tag.get('compensationTypeShortTitle')
        plan=tag.get('plan')

        programSet1 =  programSet[0:8]
        name=str(id)+' '+programSet1
        if "заочная" in programSet or "заоч" in  programSet:
            continue
        else:
            id+=1
        #eduProgramForm=tag.get('eduProgramForm')
            parser(tag,dirload+"\\"+name,programSet,plan,compensationTypeShortTitle)

        listname.append(name)
    return listname

