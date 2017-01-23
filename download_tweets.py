
# coding: utf-8

# In[ ]:

import time, os, re, requests, got, cPickle as pickle, glob, random, string, subprocess, collections, difflib
from tqdm import tqdm as progressbar
from retry import retry
from zipfile import ZipFile
rand_str = lambda n: ''.join([random.choice(string.lowercase) for i in xrange(n)])


# In[ ]:

@retry(tries=5, delay=5)
def download_url(url, stream = False):
    return requests.get(url, stream=stream, headers = {'User-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36'})


# In[ ]:

def get_closest_match(a,lst):
    """Check a against every item in lst, return
    a tuple of the closest match, its index in the
    list, and the quick_ratio"""
    match_lst = [(l,i,difflib.SequenceMatcher(None,a,l).quick_ratio()) for i,l in enumerate(lst)]
    sorted_match_lst = sorted(match_lst, key = lambda match: match[2], reverse = True)
    return sorted_match_lst[0]


# In[ ]:

def image2text(image_file):
    tmpfile = os.path.join ('ram',rand_str(10) + '.png')
    diamond_template = '''convert ORIGINAL_IMAGE -resize 400% -morphology close diamond ''' + tmpfile + ''' ; tesseract ''' + tmpfile + ''' stdout '''
    ocr_result = subprocess.check_output(diamond_template.replace('ORIGINAL_IMAGE',image_file), shell=True)
    os.remove(tmpfile)
    return ocr_result

def isolate_images(ocr_result, list_to_check, minimum_closeness=0.75):
    ocr_cleanup = [x.strip() for x in ocr_result.split('\n') if len(x) > 4 and len(re.findall(r'\w\w\w',x)) > 0]
    good_result = bool(re.findall("Your[^\n]*vote.*",ocr_result, re.IGNORECASE))
    
    if not good_result:
        return False

    # Find the line that says "Your hottest 100 votes" or "Your votes", because all the votes come after it
    OCR_CLEANUP = [x.upper() for x in ocr_cleanup]
    your_hottest_100_votes = get_closest_match('YOUR HOTTEST 100 VOTES', OCR_CLEANUP )
    your_votes = get_closest_match('YOUR VOTES', OCR_CLEANUP )
    if your_hottest_100_votes[2] > minimum_closeness:
        your_votes_index = your_hottest_100_votes[1]
    elif your_hottest_100_votes[2] < your_votes[2] and your_votes[2] > minimum_closeness:
        your_votes_index = your_votes[1]
    else:
        return False

    votes = ocr_cleanup[your_votes_index+1:]
    real_votes = []

    """ Iterate over the lines, checking them against the list
    Also check if line + the next line is on the list.
    Find the best matching line, if it meets the minimum_closeness,
    add it to the list."""
    votes_iter = iter(enumerate(votes))
    for i,vote in votes_iter:
        better_votes = [{'vote':vote,'skippable':0}]
        try:
            better_votes.append({'vote':vote+votes[i+1],'skippable':1})
            better_votes.append({'vote':vote+votes[i+1]+votes[i+2],'skippable':2})
        except IndexError:
            pass
        for bv in better_votes:
            match = get_closest_match(bv['vote'], list_to_check)
            bv['best_candidate'] = match[0]
            bv['best_score']     = match[2]
        closest_vote_in_list = sorted(better_votes , key = lambda vote: vote['best_score'], reverse = True)[0]
        if closest_vote_in_list['best_score'] > minimum_closeness:
            real_votes.append(closest_vote_in_list['best_candidate'])
            for x in range(closest_vote_in_list['skippable']):
                votes_iter.next()

    return real_votes    


# In[ ]:

def download_tweets(start,end,query):
    tweetCriteria = got.manager.TweetCriteria()
    tweetCriteria.since = start 
    tweetCriteria.until = end   
    tweetCriteria.querySearch = query    

    tweets = got.manager.TweetManager.getTweets(tweetCriteria)

    return tweets


# In[ ]:

def tweets_to_image_files(all_tweets, image_file_name_zip):

    image_zip = ZipFile(image_file_name_zip,'w')
    image_zip.close()
    
    for tweet in progressbar(all_tweets):
        shortened_tweet = tweet.text.replace(' ','')
        if 'instagram.com' in shortened_tweet:
            site  = 'instagram.com'
        elif 'twitter.com' in shortened_tweet:
            site = 'twitter.com'
        else:
            continue

        address_and_rest_of_line = 'https://' + re.findall(r' *([^ /]*'+site + r'.*)',tweet.text)[0]
        address1 = address_and_rest_of_line.split()[0]
        try:
            address2 = address_and_rest_of_line.split()[0] + address_and_rest_of_line.split()[1]
        except IndexError:
            address2 = address1

        html_page = download_url(address1)
        if html_page.status_code == 404:
            time.sleep(3)
            html_page =  download_url(address2)
            if html_page.status_code == 404:
                print('404:' + tweet.text)
                continue

        #Check for redirection
        if 'META http-equiv' in html_page.text:
            html_page = download_url(re.findall(r'URL=([^"]*)',html_page.text)[0])

        @retry(tries=5, delay=5)
        def get_image(html_page):
            try:
                image_location = re.findall(r'http[^>?"]*',re.findall(r'og:image" content[^>].*',html_page.text)[0])[0]
            except IndexError:
                return None, None
            image_data = download_url(image_location, stream=True)
            image_data.raw.decode_content = True
            d = image_data.raw.read()
            return d, image_location
        d, imagelocation = get_image(html_page)
        if d is None and imagelocation is None:
            continue
        
        user = tweet.username
        date = str(tweet.date).replace(" ","_").replace(":",'-')
        fname = user + '~' + date
        if '.jpg' in imagelocation:
            fname = fname + '.jpg'
        elif '.png' in imagelocation:
            fname = fname + '.png'
        else:
            fname = fname + '.jpg'
        #print fname
        
        image_zip = ZipFile(image_file_name_zip,'a')
        image_zip.writestr(fname, d)
        image_zip.close()

        time.sleep(4)


# In[ ]:

#tweets_to_image_files(unique_tweets,'2015.zip')


# In[3]:

def multi_process_run(func, arglist, max_processes = 7, timeout = 10):
    from tqdm import tqdm as progressbar
    from multiprocessing import Pool
    current_processes = 0
    process_list = []
    #outputs = []
    results = []
    for arg in progressbar(arglist):
        if current_processes == max_processes:
            process_and_output = process_list.pop(0)
            results.append(process_and_output[1].get(timeout=timeout))
            process_and_output[0].close()
            current_processes = current_processes - 1
            
        p = Pool (processes = 1)
        output = p.apply_async(func,arg)
        process_list.append((p,output,arg))
        current_processes = current_processes + 1
    # Get any processes still running
    for process in process_list:
        results.append(process[1].get(timeout=timeout))
        process[0].close()

    return results
    


# In[4]:

def zip_to_texts(zip_filename, processes=7, timeout=600):
    zf = ZipFile(zip_filename)
    
    tmpdir = os.path.join('ram','tmp'+rand_str(10))
    os.mkdir (tmpdir)
    zf.extractall(tmpdir)
    filenames = glob.glob(os.path.join(tmpdir,'*'))
    #arguments = [(filename, compare_list) for filename in filenames]
    
    results = multi_process_run_fast(image2text,filenames,processes,timeout)
    
    for filename in filenames:
        os.remove(filename)
    os.rmdir(tmpdir)
    
    simple_filenames = [os.path.split(filename)[-1] for filename in filenames]
    
    return zip (simple_filenames, results)
    


# In[ ]:

def multi_process_run_fast(func, arglist, max_processes = 14, timeout = 30):
    from tqdm import tqdm as progressbar
    from multiprocessing import Pool
    current_processes = 0
    process_list = []
    results = []
    for i,arg in progressbar(enumerate(arglist)):
        if current_processes == max_processes:
            while True not in [p[1].ready() for p in process_list]:
                time.sleep(0.1)
            finished_process = [p[1].ready() for p in process_list].index(True)
            process_and_output = process_list.pop(finished_process)
            results[process_and_output[3]] = process_and_output[1].get(timeout=timeout)
            process_and_output[0].close()
            current_processes = current_processes - 1
            
        p = Pool (processes = 1)
        output = p.apply_async(func,(arg,))
        results.append(None)
        process_list.append((p,output,arg,i))
        current_processes = current_processes + 1
    # Get any processes still running
    for process in process_list:
        results[process[3]] = process[1].get(timeout=timeout)
        process[0].close()

    return results


# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:



