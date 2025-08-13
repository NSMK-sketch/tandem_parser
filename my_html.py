import jinja2
import xml.etree.ElementTree as ET 
from datetime import datetime
def parser(tag, file_name, programSet, plan, compensationTypeShortTitle):
    with open(file_name+".html", mode="w", encoding='utf-8-sig') as file_writer:
        current_datetime = datetime.now()
        time = current_datetime.strftime("%Y-%m-%d %H:%M")
        items = []
        
        for tagen in tag.findall('entrant/row'):
            statusCode = tagen.attrib['statusCode']
            benefitSpecialCategory = tagen.attrib.get('benefitSpecialCategory')
            
            if benefitSpecialCategory is not None:
                benefitSpecialCategory = "✓"
            else:
                benefitSpecialCategory = " "
                
            if statusCode == "7" or statusCode == "8":
                continue
                
            # Получаем firstRating - теперь ищем его среди дочерних элементов row
            first_rating = tagen.find('firstRating')
            rank = first_rating.text if first_rating is not None else "0"  # значение по умолчанию, если тег не найден
            
            fullFio = tagen.attrib['fullFio']
            fullFio = fullFio.capitalize().title()
            
            averageEduInstitutionMark = tagen.attrib['averageEduInstitutionMark']
            originalSubmissionWay = tagen.attrib['originalIn']
            priority = tagen.attrib['priority']
            acceptedEntrantDate = tagen.attrib.get('acceptedEntrantDate')
            
            averageEduInstitutionMark = averageEduInstitutionMark.replace(',', '.')    
            
            if originalSubmissionWay == 'false':
                originalSubmissionWay = 'НЕТ'
            else:
                originalSubmissionWay = 'ДА'
                if compensationTypeShortTitle == "по договору":
                    if acceptedEntrantDate is None:
                        originalSubmissionWay = 'НЕТ'

            an_item = dict(
                rank=rank,
                fullFio=fullFio,
                originalSubmissionWay=originalSubmissionWay,
                averageEduInstitutionMark=averageEduInstitutionMark,
                benefitSpecialCategory=benefitSpecialCategory
            )
            items.append(an_item)
            
        loader = jinja2.FileSystemLoader('templates\\page.htm')
        env = jinja2.Environment(loader=loader)
        template = env.get_template('')
        msg = template.render(
            items=items,
            time=time,
            programSet=programSet,
            plan=plan,
            compensationTypeShortTitle=compensationTypeShortTitle
        )
        
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

