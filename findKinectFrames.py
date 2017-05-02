import os
from datetime import datetime
import shutil
from decimal import Decimal
from subprocess import Popen, PIPE
import sys


#check version
if sys.version_info <= (3,0):
    #py2
    write_format = 'wb'
else:
    #py3
    write_format = 'w'


output_len = 10
frame_rate = 60.0


def chunks(l, n):
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]


def batch(parent_dir, temp_dir, batch_vid_dir):
    imgs = list(os.listdir(parent_dir))
    total_size = len(imgs)
    batch_size = int(total_size / 10)
    groups = chunks(imgs, batch_size)
    for sub in groups:
        # eliminate small groups
        if groups.index(sub) > 0:
            if len(groups[groups.index(sub)]) < batch_size:
                groups[groups.index(sub)-1].extend(groups[groups.index(sub)])
                groups.remove(groups[groups.index(sub)])
    for sub2 in groups:
        if groups.index(sub2) > 0:
            groups[groups.index(sub2)].insert(0, groups[groups.index(sub2) - 1][-1])
    num = 1
    for sub3 in groups:
        ext = prep(sub3, parent_dir, temp_dir)
        convert(ext, temp_dir, num, batch_vid_dir)
        clear(temp_dir)
        num += 1
    return


def prep(sub_batch, par_dir, tem_dir):
    if not os.path.exists(tem_dir):
        os.makedirs(tem_dir)
    
    if ".DS_Store" in sub_batch:
        sub_batch.remove(".DS_Store")
    if "temp" in sub_batch:
        sub_batch.remove("temp")

    space = str(int(Decimal(1.0/frame_rate)*1000000)).zfill(6)
    offset_str = '0-00-00-'+space

    n = 0
    zero = datetime.strptime(os.path.splitext(sub_batch[0])[0], '%H-%M-%S-%f')
    previousTime = zero
    offset = datetime.strptime(offset_str, '%H-%M-%S-%f')-datetime.strptime('0-00-00-00', '%H-%M-%S-%f')
    for img in sub_batch:
        ext = os.path.splitext(img)[1]
        img_path = os.path.join(par_dir, img)
        time = datetime.strptime(os.path.splitext(img)[0], '%H-%M-%S-%f')
        while (previousTime-zero) < (time-zero):
            out_name = str(n + 1).zfill(output_len)+ext
            out_path = os.path.join(tem_dir, out_name)
            shutil.copy(img_path, out_path)
            n += 1
            previousTime += offset
    return ext


def convert(ext, temp, num, out):
    if not os.path.exists(out):
        os.makedirs(out)
    vid_num = str(num).zfill(output_len) + ".mp4"
    ffmpeg_cmd = 'ffmpeg -framerate {0} -i {1}/%10d{4} -c:v libx264 {2}/{3}'
    temp = '"' + temp + '"'
    out = '"' + out + '"'
    input_rate = '"' + str(int(frame_rate)) + '"'
    p = Popen(ffmpeg_cmd.format(input_rate, temp, out, vid_num, ext), stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = p.communicate(input=None)
    return stdout, stderr


def video_concat(txt_file, out_video):
    ffmpeg_cmd = 'ffmpeg -f concat -safe 0 -i {0} -c copy {1}'
    txt_file = '"' + txt_file + '"'
    out_video = '"' + out_video + '"'
    p = Popen(ffmpeg_cmd.format(txt_file, out_video), stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = p.communicate(input=None)
    return stdout, stderr


def clear(tem_dir):
    shutil.rmtree(tem_dir)
    return


def combine(batch_dir, out, id):
    data = []
    temp_file = os.path.join(batch_dir, "temp.txt")
    videoName = id+"_kinect_video.mp4"
    out_file = os.path.join(out, videoName)
    if not os.path.exists(out):
        os.makedirs(out)
    with open(temp_file, write_format) as temp_txt:
        for el in os.listdir(batch_dir):
            if "temp" not in el:
                data.append('file '+"'"+os.path.join(batch_dir, el)+"'\n")
        temp_txt.writelines(data)
    video_concat(temp_file, out_file)
    shutil.rmtree(batch_dir)
    return


def firstPass(dataDir):
    kinectDirList = []
    sessions = [x for x in os.listdir(dataDir) if x != ".DS_Store"]
    for session in sessions:
        sessionPath = os.path.join(dataDir,session)
        for contents in os.listdir(sessionPath):
            if "Kinect" in contents:
                kinectDir = os.path.join(sessionPath,contents)
                for el in os.listdir(kinectDir):
                    kinectDirList.append(os.path.join(kinectDir,el))
    return kinectDirList


def secondPass(kinectDirList):
    cleanKinectDirList = [x for x in kinectDirList if ".DS_Store" not in x]
    for el in cleanKinectDirList:
        id = os.path.basename(el).split('_')[0]
        video = id+"_kinect_video.mp4"
        if video in os.listdir(el):
            print id, 'already done... skipping'
        else:
            print 'processing', id+'...'
            framePath = os.path.join(el,[x for x in os.listdir(el) if x == "frames"][0])
            colorPath = os.path.join(framePath,[x for x in os.listdir(framePath) if x == "color"][0])
            
            temp_dir = os.path.join(framePath,'temp')
            batch_vid_dir = os.path.join(framePath,'batch_videos')
            out_dir = el
            
            batch(colorPath, temp_dir, batch_vid_dir)
            combine(batch_vid_dir, out_dir, id)
            print id, 'done...'
    return


if __name__ == '__main__':
    dataDir = "/Volumes/Data/smoke-backup/Data"
    kinectDirList = firstPass(dataDir)
    screenedKinectList = secondPass(kinectDirList)