import psycopg2
import os
import psycopg2.extras


# Get frequencies of words and set them to the database
def get_freq(response, genius, worddata, user):
    datab = psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')
    db = datab.cursor()
    datab.autocommit = True
    wordbundle = []
    ratios = {}
    # Go through every song and make one giant string with all the counts of words (with some things excluded)
    for item in response['items']:
        name = item['name']
        artist = item['artists'][0]['name']
        lyrics = getlyrics(name, artist, genius)
        if not lyrics:
            continue
        lyrics = lyrics.split("\n")
        for i in lyrics:
            if i:
                if i[0] == "[" and i[-1] == "]":
                    lyrics.remove(i)
        lyrics = ' '.join(lyrics) 
        wordbundle.append(lyrics.upper())
    collapsebundle = ' '.join(wordbundle)
    # remove punctuation
    collapsebundle = collapsebundle.replace("'", "").replace("]", "").replace("[", "").replace("!", "").replace(".", "").replace(",", "").replace("(", "").replace(")", "").replace("{",
    "").replace("}", "").replace("?", "").replace(":", "").replace(";", "").replace(r"VERSE |[1|2|3]|CHORUS|BRIDGE|OUTRO", "").replace("[", "").replace("]", "").replace(r"INSTRUMENTAL|INTRO|GUITAR|SOLO", "")
    # Get dict with count of each word
    big = word_count(collapsebundle)
    total = 0
    for key in big:
        total += int(big[key])
    for key in big:
        if key in worddata:
            # Append to ratios the fraction each word is
            ratios[key] = float(big[key])/float(worddata[key])/total
  
    ratiot = [(k, v) for k, v in ratios.items()]
    ratiot.sort(key=lambda x: x[1])   
    # Update database, remove the last data the user generated
    db.execute("SELECT * FROM userfreqs WHERE id=%s", (int(user),))
    if db.fetchall():
        db.execute("DELETE FROM userfreqs WHERE id = %s", (int(user),))
        datab.commit()
    for i in ratiot:
        db.execute("INSERT INTO userfreqs (id, word, freq) VALUES (%s, %s, %s)", (int(user), i[0], i[1]))
        datab.commit()
    db.execute("INSERT INTO userfreqs (id, word, freq) VALUES (%s, %s, %s)", (4, "hello", 0.9))
    datab.commit()
    
    return(ratiot)


# Gets the text of song lyrics using Genius API
def getlyrics(song, artist, genius):
    # Hyphens usually separate title from irrelevant information. Get rid of everything after.
    if " - " in song:
        searchname = song.split(" - ", 1)[0] 
    else:
        searchname = song
    searchname = searchname.replace('(', '').replace(')', '')
    song = genius.search_song(searchname, artist)       
    if song:
        return(song.lyrics)
    else:
        return


# Count those words baby
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