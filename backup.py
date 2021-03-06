#!/usr/bin/env python3

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from hurry.filesize import size
from pyrfc3339 import parse
from magic import from_file
import io, datetime, os

def authenticate(apiName, apiVersion, apiScope):
    ''' Authenticate the user and returns a service object
    @apiName should be the name of the google api
    found here: https://developers.google.com/api-client-library/python/apis/
    @apiVerison should be the version of the api
    @apiScope should be the scope of the google api, this script uses OAuth2 Service Accounts
    found here: https://developers.google.com/identity/protocols/googlescopes '''

    #specify service account file (contains service account information)
    SERVICE_ACCOUNT_FILE = '../drive0.json'
    #create a credentials object with the service account file and the specificed scope
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=apiScope)
    #build the service object
    service = build(apiName, apiVersion, credentials=credentials)
    #return the service object
    return service

''' ---REMOTE GET METHODS---'''
def getFileDictionary(service):
    ''' Return a dictionary with the format files{name:id}
    @service should be the service object generated in authenticate '''

    # Call the Drive v3 API
    results = service.files().list(fields="files(id, name, size, md5Checksum, modifiedTime, mimeType)").execute().get('files')
    files = []
    #loop through all items in array
    for item in results:
        #if the item is a file
        if item['mimeType'] != 'application/vnd.google-apps.folder':
            #remove from the list
            files.append(item)
    # return an array of files with their associated id
    return files

def getDirectoryDictionary(service):
    ''' Return a dictionary containing all of the directories
    @service should be the service object generated in authenticate '''

    # Call the Drive v3 API
    results = service.files().list(fields="files(id, name, size, md5Checksum, modifiedTime, mimeType)").execute().get('files')
    directories = []
    #loop through all items in array
    for item in results:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            #add to the list
            directories.append(item)
    return directories


def getFileMetadata(service, fileName):
    ''' Get the metadata of a file
    @fileId is the id of the file
    @service is the service object '''

    #return the metadata of the file
    return service.files().get(fileId=getFileId(service, fileName)).execute()

def getDriveUseage(service):
    ''' Checks the drive useage for a service object
    @service should be a service object from the authenticate method '''

    #return the storage quota of the current service object
    return service.about().get(fields='storageQuota').execute().get('storageQuota')

def getFileId(service, fileName):
    ''' Gets the file id of the specified file
    @service should be the service object
    @fileName should be the name of the file'''

    #initlize return variable
    fileId = ''
    #get the list of files
    fileList = getFileDictionary(service)
    #loop through the all the files
    for file in fileList:
        #if the file name exists
        if fileName in file['name']:
            #set the return value
            fileId = file['id']
    #return the file id of the file
    return fileId

def getDirectoryId(service, directoryName):
    ''' Gets the file id of the specified file
    @service should be the service object
    @directoryName should be the name of the directory'''

    directoryId = ''
    #get all the directories
    directoryList = getDirectoryDictionary(service)
    #loop through all the directories
    for directory in directoryList:
        #the directory matches the name
        if directory['name'] == directoryName:
            #set the directory id
            directoryId = directory['id']
    #return the id of the directory
    return directoryId

''' ---PRINT METHODS--- '''
def printAllFiles(fileDictionary):
    ''' Prints out a list of files from a dictionary
    @fileDictionary should be a dictionary containing filenames and file ids '''

    #formating string
    format = "{0:16} {1:34} {2:6} {3:20} {4:5}"
    #print the column names
    print(format.format("Name", "Id", "Size", "Modified", "Hash"))
    #for each file print out its respective column
    for file in fileDictionary:
        print (format.format(file['name'], file['id'],
                                    size(int(file['size'])),
                                    parse(file['modifiedTime']).strftime('%m/%d/%Y-%H:%M:%S'),
                                    file['md5Checksum']))

def printStorageQuota(storageQuota):
    ''' Prints the storage quota for the current service object
    @storageQuota should be the result returned from about.get() '''

    #get google drive limit
    limit = float(storageQuota['limit'])
    #get the usage of the drive
    usage = float(storageQuota['usage'])
    #get the usage percentage
    usagePercentage = ("{0:.2f}".format(usage/limit))
    #set table format values
    tableFormatting = "{0:7} {1:6} {2:10}"
    #print out the results
    print(tableFormatting.format("Limit", "Usage", "Percentage\n") +
        tableFormatting.format(size(limit), size(usage), usagePercentage + "%"))

''' ---REMOTE FILE MANAGEMENT--- '''
def uploadFile(service, fileName, directoryName):
    ''' Uploads a file to a specificed location in the drive
    @fileName should be the file that should be uploaded
    @service should be a service object from the authenticate method '''

    #check the mimetype
    mimetype = from_file(fileName, mime=True)
    #creates a media file upload object
    ###consider chunk size in the future
    media = MediaFileUpload(fileName, mimetype=mimetype)
    #creates a new file
    file = service.files().create(body={'name': fileName.split('/')[-1], 'parent' : getDirectoryId(service, directoryName)},
                                media_body=media).execute()

def uploadFileList(service, fileList):
    ''' Uploads a list of files
    @service should be a service object
    @fileList is the list of files'''

    #for each file, upload it
    for file in fileList:
        uploadFile(file, service)

def downloadFile(service, fileName):
    ''' Downloads the file to the current working directory
    @fileId should be a file id
    @service should be a service object from the authenticate method '''

    #create a file to write the bytes too
    fileBuffer = io.FileIO(f'./{fileName}', 'wb')
    #get the file's content
    request = service.files().get_media(fileId=getFileId(service, fileName))
    #create the download object, pass in fileBuffer and service request
    downloader = MediaIoBaseDownload(fileBuffer, request)
    done = False
    #while the file is downloading show progress
    while done is False:
        #download the next chunk, if it is done escape the loop
        status, done = downloader.next_chunk()
        #print the current progress to the screen
        print (f"Download {int(status.progress() * 100)}%.")
    #close the file so it can be opened elsewhere
    fileBuffer.close()

def deleteFile(service, fileName):
    ''' Deletes a specified file
    @service should be a service object
    @fileName should be the file that should be deleted '''

    #delete the file
    service.files().delete(fileId=getFileId(service, fileName)).execute()

def shareFile(fileId, service, email):
    ''' Shares a file with a specified user
    @fileId, shared file id
    @service is the service object from the authenticate method
    @email is the email of who you are sharing the file with'''

    #create the permission body
    permission = {'type':'user', 'role':'writer', 'emailAddress':email}
    #create the permission with the associated file
    service.permissions().create(fileId=fileId, body=permission).execute()

def createDirectory(service, directoryName):
    file_metadata = {'name': directoryName,'mimeType': 'application/vnd.google-apps.folder'}
    service.files().create(body=file_metadata).execute()

''' ---LOCAL FILE METHODS---'''
def getContents(directory):
    return os.listdir(directory)

def getLocalDirectories(directory, contents):
    directoryList = []
    for item in contents:
        if os.path.isdir(directory + item):
            directoryList.append(directory + item)
    return directoryList

def getLocalFiles(directory, contents):
    fileList = []
    for item in contents:
        if os.path.isfile(directory + item):
            fileList.append(directory + item)
    return fileList

def main():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    service = authenticate('drive', 'v3', SCOPES)
    files =  getFileDictionary(service)
    folder = getDirectoryDictionary(service)
    #createDirectory(service, 'folder')
    #print(getFileMetadata(service, 'file1.txt'))
    #deleteFile(service, 'folder')
    printAllFiles(getFileDictionary(service))
    print(folder)
    #createDirectory(service, 'test-folder2')
    #print (getDirectoryId(service, 'test-folder2'))
    #uploadFile(service, './test-folder/test-folder2/passwords', 'test-folder2')
    #printStorageQuota(getDriveUseage(service).get('storageQuota'))

if __name__ == "__main__": main()
