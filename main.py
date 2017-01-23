
# coding: utf-8

# # Download the tweets from '2015-12-09' to '2016-01-23' with the words 'triplej', 'triplejhottest100', and/or 'hottest100'

# In[2]:

import pickle, tqdm
from download_tweets import *
from tqdm import tqdm as progressbar


# In[ ]:

keywords = ['triplej','triplejhottest100','hottest100']
tweets_2015 = []
for keyword in keywords:
    tweets = download_tweets('2015-12-09', '2016-01-23', keyword)
    tweets_2015.extend(tweets)
tweets_2015 = list(set(tweets_2015))
pickle.dump(tweets_2015, open( "tweets_2015.pickle", "wb"))


# # Go through each tweet, and see if it has a twitterpic or instgram link.  If so, download it, and save it to a zip file.

# In[ ]:

tweets_to_image_files(tweets_2015, 'tweets_2015.zip')


# # Now OCR each image and look for 'Your votes' or 'Your hottest 100 votes'.  With the ones that do, try to interpret the image against the top 200 winners of 2015.

# In[ ]:

ocr_votes_2015 = zip_to_texts('tweets_2015.zip')
pickle.dump(ocr_votes_2015, open( "ocr_votes_2015.pickle", "wb"))


# In[49]:

ocr_votes_2015 = pickle.load(open( "ocr_votes_2015.pickle"))
top_200_winners_text = open('2015_winners.txt').readlines()
top_200_winners = [' '.join(x.split(' ')[1:]).strip() for x in top_200_winners_text]

votes_2015 = []
for ocr_result in progressbar(ocr_votes_2015):
    vote_list = isolate_images(ocr_result[1], top_200_winners)
    vote = {'user':ocr_result[0].split('~')[0],'filename':ocr_result[0],
            'text':ocr_result[1], 'votes': vote_list}
    votes_2015.append(vote)
pickle.dump(votes_2015, open( "votes_2015.pickle", "wb"))


# # Filter for only the ones with an actual vote image, and assign them a score

# In[59]:

votes_2015 = pickle.load(open( "votes_2015.pickle"))

filtered_votes_2015 = [v for v in votes_2015 if v['votes'] != False and v['votes'] != [] ]

for fv in filtered_votes_2015:
    harmonic_score, descending_score, flat_score = 0.0, 0.0, 0.0
    for vote in fv['votes']:
        harmonic_score   = harmonic_score + 1.0 / (top_200_winners.index(vote)+1.0)
        descending_score = descending_score + 201 - top_200_winners.index(vote)
    fv['harmonic_score']   = harmonic_score
    fv['descending_score'] = descending_score

filtered_votes_2015 = sorted (filtered_votes_2015, key = lambda fv: fv['harmonic_score'], reverse= True)


# # Let's see how those scores stack up

# In[60]:

import matplotlib.pyplot as plt

for score_type in ('harmonic_score','descending_score'):
    scores = sorted([fv[score_type] for fv in filtered_votes_2015 if fv[score_type] != 0.0], reverse = True)
    avg = str(sum(scores) / len(scores))
    med = str(scores[len(scores)//2])
    plt.title(score_type + ', avg: ' + avg + ', median: ' + med)
    plt.hist(scores)
    plt.show()


# # Now for 2016
# ## Download the tweets from '2016-12-09' to '2017-01-24' with the words 'triplej', 'triplejhottest100', and/or 'hottest100'

# In[ ]:

keywords = ['triplej','triplejhottest100','hottest100']
tweets_2016 = []
for keyword in keywords:
    tweets = download_tweets('2016-12-09', '2017-01-24', keyword)
    tweets_2016.extend(tweets)
tweets_2016 = list(set(tweets_2016))
pickle.dump(tweets_2016, open( "tweets_2016.pickle", "wb"))


# # Go through each tweet, and see if it has a twitterpic or instgram link. If so, download it, and save it to a zip file.

# In[ ]:

tweets_to_image_files(tweets_2016, 'tweets_2016.zip')


# # Now OCR each image and look for 'Your votes' or 'Your hottest 100 votes'.  With the ones that do, try to interpret the image against the shortlist for 2016.

# In[45]:

ocr_votes_2016 = zip_to_texts('tweets_2016.zip')
pickle.dump(ocr_votes_2016, open( "ocr_votes_2016.pickle", "wb"))


# In[46]:

ocr_votes_2016 = pickle.load(open( "ocr_votes_2016.pickle"))
shortlist_2016 = open('2016_shortlist.txt').readlines()

votes_2016 = []
for ocr_result in progressbar(ocr_votes_2016):
    vote_list = isolate_images(ocr_result[1], shortlist_2016)
    vote = {'user':ocr_result[0].split('~')[0],'filename':ocr_result[0],
            'text':ocr_result[1], 'votes': vote_list}
    votes_2016.append(vote)
pickle.dump(votes_2016, open( "votes_2016.pickle", "wb"))


# # Now the Moment of Truth -- Assign the weights to each song and print them out

# In[90]:

votes_2016 = pickle.load(open( "votes_2016.pickle" ))
votes_2016 = [v for v in votes_2016 if v['votes'] is not False]

def weight_songs(score_type, default_score):
    songs_2016 = {}
    for v in progressbar(votes_2016):
        v_2015 = [v15 for v15 in filtered_votes_2015 if v15['user'] == v['user'] and score_type in v15.keys()]
        if v_2015:
            weighting = v_2015[0][score_type]
        else:
            weighting = default_score
        for vote in v['votes']:
            if vote not in songs_2016.keys():
                songs_2016[vote] = weighting
            else:
                songs_2016[vote] = songs_2016[vote] + weighting
    return songs_2016


# In[91]:

default_score = sum([fv['descending_score'] for fv in filtered_votes_2015]) / len([fv['descending_score'] for fv in filtered_votes_2015])
songs = weight_songs('descending_score', default_score)
for i, song_weight in enumerate(sorted(songs, key=songs.get, reverse = True)[:200]):
    print i+1, song_weight.strip(), songs[song_weight]


# In[92]:

default_score = sum([fv['harmonic_score'] for fv in filtered_votes_2015]) / len([fv['harmonic_score'] for fv in filtered_votes_2015])
songs = weight_songs('harmonic_score', default_score)
for i, song_weight in enumerate(sorted(songs, key=songs.get, reverse = True)):
    print i+1, song_weight.strip(), songs[song_weight]


# In[93]:

default_score = 1
songs = weight_songs('flat_score', default_score)
for i, song_weight in enumerate(sorted(songs, key=songs.get, reverse = True)):
    print i+1, song_weight.strip(), songs[song_weight]


# In[ ]:



