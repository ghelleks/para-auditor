-- AppleScript to extract folder structure from Apple Notes
-- Returns JSON-like structure with Projects and Areas folders

on run
    try
        tell application "Notes"
            set projectFolders to {}
            set areaFolders to {}
            set allFolders to every folder
            
            -- Look for Projects and Areas parent folders
            set projectsParent to missing value
            set areasParent to missing value
            
            repeat with theFolder in allFolders
                set folderName to name of theFolder
                if folderName is "Projects" then
                    set projectsParent to theFolder
                else if folderName is "Areas" then
                    set areasParent to theFolder
                end if
            end repeat
            
            -- Extract subfolders from Projects folder
            if projectsParent is not missing value then
                try
                    set subfolders to every folder of projectsParent
                    repeat with subfolder in subfolders
                        set end of projectFolders to name of subfolder
                    end repeat
                end try
            end if
            
            -- Extract subfolders from Areas folder
            if areasParent is not missing value then
                try
                    set subfolders to every folder of areasParent
                    repeat with subfolder in subfolders
                        set end of areaFolders to name of subfolder
                    end repeat
                end try
            end if
            
            -- Format as JSON-like string
            set projectsJSON to "["
            repeat with i from 1 to count of projectFolders
                set projectsJSON to projectsJSON & "\"" & (item i of projectFolders) & "\""
                if i < count of projectFolders then
                    set projectsJSON to projectsJSON & ","
                end if
            end repeat
            set projectsJSON to projectsJSON & "]"
            
            set areasJSON to "["
            repeat with i from 1 to count of areaFolders
                set areasJSON to areasJSON & "\"" & (item i of areaFolders) & "\""
                if i < count of areaFolders then
                    set areasJSON to areasJSON & ","
                end if
            end repeat
            set areasJSON to areasJSON & "]"
            
            return "{\"projects\":" & projectsJSON & ",\"areas\":" & areasJSON & "}"
        end tell
    on error errMsg
        return "{\"error\":\"" & errMsg & "\"}"
    end try
end run