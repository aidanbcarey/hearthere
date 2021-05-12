import psycopg2
import os
import psycopg2.extras
def get_freq(response,genius,worddata,user):
    datab=psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')
    db=datab.cursor(cursor_factory=psycopg2.extras.DictCursor)
    wordbundle=[]
    ratios={}
    for item in response['items']:
        name=item['name']
        artist=item['artists'][0]['name']
        lyrics=getlyrics(name,artist,genius)
        if not lyrics:
            continue
        lyrics=lyrics.split("\n")
        for i in lyrics:
            if i:
                if i[0]=="[" and i[-1]=="]":
                    lyrics.remove(i)
        lyrics=' '.join(lyrics)
        wordbundle.append(lyrics.upper())
    collapsebundle=' '.join(wordbundle)
    collapsebundle=collapsebundle.replace("'","").replace("]","").replace("[","").replace("!","").replace(".","").replace(",","").replace("(","").replace(")","").replace("{","").replace("}","").replace("?","").replace(":","").replace(";","").replace(r"VERSE |[1|2|3]|CHORUS|BRIDGE|OUTRO","").replace("[","").replace("]","").replace(r"INSTRUMENTAL|INTRO|GUITAR|SOLO","")
    big=word_count(collapsebundle)
    total=0
    for key in big:
        total+=int(big[key])
    for key in big:
        if key in worddata:
            ratios[key]=float(big[key])/float(worddata[key])/total
    lyrics=ratios["THE"]
    ratiot = [(k, v) for k, v in ratios.items()]
    ratiot.sort(key = lambda x: x[1])   
    ratiot=ratiot[1:10]
    if db.execute("SELECT FROM userfreqs WHERE user= %s",(user,)):
        db.execute("DELETE FROM userfreqs WHERE user= %s",(user,))
    for i in ratriot:
        db.execute("INSERT INTO userfreqs (user, word, freq) VALUES (%s, %s, %s)",(user,i[0],i[1]))
    return(ratiot)

def getlyrics(song,artist,genius):
    if " - " in song:
        searchname = song.split(" - ", 1)[0] 
    else:
        searchname=song
    searchname=searchname.replace('(','').replace(')','')
    song = genius.search_song(searchname, artist);       
    if song:
        return(song.lyrics)
    else:
        return

def word_count(str):
    counts = dict()
    words = str.split()

    for word in words:
        if word.isalpha():
            if word in counts:
                counts[word] += 1
            else:
                counts[word] = 1

    return counts