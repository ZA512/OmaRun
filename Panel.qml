import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "components" as Components

Panel {
  id: root
  moduleName: "io.github.mgirard.omarun"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  property var tasks: []
  property string selectedTaskId: ""
  property bool showingEditor: false
  property bool editingTask: false
  property bool confirmingDelete: false
  property bool returnToEditorAfterDeleteCancel: false
  property int selectedListIndex: -1
  property string editorName: ""
  property string editorCommand: ""
  property string editorArguments: ""
  property string editorWorkingDirectory: ""
  property int editorTimeoutSeconds: 0
  property bool editorAdvancedExpanded: false
  property bool editorScheduleEnabled: false
  property string editorScheduleMode: "every-hours"
  property int editorScheduleInterval: 6
  property string editorScheduleTime: "03:00"
  property var editorScheduleWeekdays: []
  property string detailsStatusText: ""
  property string detailsLogText: ""
  property string detailsNextRunText: ""
  property string errorText: ""

  readonly property var selectedTask: {
    for (var i = 0; i < root.tasks.length; i++) {
      if (String(root.tasks[i].id) === root.selectedTaskId) return root.tasks[i]
    }
    return null
  }

  function open() {
    refreshTasks()
    root.controller.show()
  }

  function close() {
    root.controller.hide()
  }

  function toggle() {
    if (root.opened) close()
    else open()
  }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function")
      return root.bar.switchPanelFrom(root.hostWidget || root, direction)
    return false
  }

  function backendScriptPath() {
    var resolved = Qt.resolvedUrl("backend/omarunctl.py").toString()
    if (resolved.indexOf("file://") === 0) return decodeURIComponent(resolved.substring(7))
    return resolved
  }

  function parseJson(raw) {
    try { return JSON.parse(String(raw || "")) } catch (e) { return null }
  }

  function buildScheduleObject() {
    if (!editorScheduleEnabled) return {"enabled": false}
    return {
      "enabled": true,
      "mode": editorScheduleMode,
      "interval": editorScheduleInterval,
      "time": editorScheduleTime,
      "weekdays": editorScheduleWeekdays
    }
  }

  function refreshTasks() {
    if (listProc.running) return
    listProc.command = ["python3", backendScriptPath(), "list"]
    listProc.running = true
  }

  function ensureSelectedIndex() {
    if (!root.tasks || root.tasks.length === 0) {
      root.selectedListIndex = -1
      return
    }
    if (root.selectedListIndex < 0) {
      root.selectedListIndex = 0
      return
    }
    if (root.selectedListIndex >= root.tasks.length) root.selectedListIndex = root.tasks.length - 1
  }

  function runAction(action, taskId) {
    if (actionProc.running) return
    actionProc.command = ["python3", backendScriptPath(), action, "--id", taskId]
    actionProc.running = true
  }

  function openDetails(taskId) {
    detailsStatusText = ""
    detailsLogText = ""
    detailsNextRunText = ""
    selectedTaskId = taskId
    showingEditor = false
    refreshStatus(taskId)
    refreshLog(taskId)
  }

  function toggleDetails(taskId) {
    if (selectedTaskId === taskId) {
      selectedTaskId = ""
      detailsStatusText = ""
      detailsLogText = ""
      detailsNextRunText = ""
      return
    }
    openDetails(taskId)
  }

  function openAddEditor() {
    editingTask = false
    showingEditor = true
    confirmingDelete = false
    returnToEditorAfterDeleteCancel = false
    selectedTaskId = ""
    errorText = ""
    editorName = ""
    editorCommand = ""
    editorArguments = ""
    editorWorkingDirectory = ""
    editorTimeoutSeconds = 0
    editorAdvancedExpanded = false
    editorScheduleEnabled = false
    editorScheduleMode = "every-hours"
    editorScheduleInterval = 6
    editorScheduleTime = "03:00"
    editorScheduleWeekdays = []
    taskEditor.loadValues({
      "name": "",
      "command": "",
      "arguments": "",
      "workingDirectory": "",
      "timeoutSeconds": 0,
      "advancedExpanded": false,
      "scheduleEnabled": false,
      "scheduleMode": "every-hours",
      "scheduleInterval": 6,
      "scheduleTime": "03:00",
      "scheduleWeekdays": []
    })
  }

  function openEditEditor(task) {
    if (!task) return
    editingTask = true
    showingEditor = true
    confirmingDelete = false
    returnToEditorAfterDeleteCancel = false
    errorText = ""
    editorName = String(task.name || "")
    editorCommand = String(task.command || "")
    editorArguments = String(task.arguments || "")
    editorWorkingDirectory = String(task.workingDirectory || "")
    editorTimeoutSeconds = Number(task.timeoutSeconds || 0)
    editorAdvancedExpanded = false
    var schedule = task.schedule || {}
    editorScheduleEnabled = schedule.enabled === true
    editorScheduleMode = String(schedule.mode || "every-hours")
    editorScheduleInterval = Number(schedule.interval || 6)
    editorScheduleTime = String(schedule.time || "03:00")
    editorScheduleWeekdays = schedule.weekdays || []
    taskEditor.loadValues({
      "name": root.editorName,
      "command": root.editorCommand,
      "arguments": root.editorArguments,
      "workingDirectory": root.editorWorkingDirectory,
      "timeoutSeconds": root.editorTimeoutSeconds,
      "advancedExpanded": false,
      "scheduleEnabled": root.editorScheduleEnabled,
      "scheduleMode": root.editorScheduleMode,
      "scheduleInterval": root.editorScheduleInterval,
      "scheduleTime": root.editorScheduleTime,
      "scheduleWeekdays": root.editorScheduleWeekdays
    })
  }

  function requestDelete(task, returnToEditor) {
    if (!task) return
    if (!root.showingEditor || !root.editingTask) root.openEditEditor(task)
    root.returnToEditorAfterDeleteCancel = returnToEditor === true
    root.confirmingDelete = true
  }

  function cancelDeleteConfirmation() {
    root.confirmingDelete = false
    if (!root.returnToEditorAfterDeleteCancel) {
      root.showingEditor = false
      root.editingTask = false
    }
    root.returnToEditorAfterDeleteCancel = false
  }

  function refreshStatus(taskId) {
    if (statusProc.running) return
    statusProc.taskId = taskId
    statusProc.command = ["python3", backendScriptPath(), "status", "--id", taskId]
    statusProc.running = true
  }

  function refreshLog(taskId) {
    if (logProc.running) return
    logProc.taskId = taskId
    logProc.command = ["python3", backendScriptPath(), "log", "--id", taskId]
    logProc.running = true
  }

  function addTask() {
    var taskName = String(editorName || "").trim()
    var taskCommand = String(editorCommand || "").trim()
    if (taskName === "" || taskCommand === "") {
      errorText = "Name and command are required."
      return
    }
    if (addProc.running) return
    var command = [
      "python3", backendScriptPath(), "add",
      "--name", taskName,
      "--command", taskCommand,
      "--arguments", editorArguments,
      "--working-directory", editorWorkingDirectory,
      "--timeout-seconds", String(editorTimeoutSeconds),
      "--schedule", JSON.stringify(buildScheduleObject())
    ]
    addProc.command = command
    addProc.running = true
  }

  function updateTask() {
    if (!selectedTask || selectedTask.running === true) {
      errorText = "Stop task before editing."
      return
    }
    var taskName = String(editorName || "").trim()
    var taskCommand = String(editorCommand || "").trim()
    if (taskName === "" || taskCommand === "") {
      errorText = "Name and command are required."
      return
    }
    if (updateProc.running) return
    var command = [
      "python3", backendScriptPath(), "update",
      "--id", String(selectedTask.id),
      "--name", taskName,
      "--command", taskCommand,
      "--arguments", editorArguments,
      "--working-directory", editorWorkingDirectory,
      "--timeout-seconds", String(editorTimeoutSeconds),
      "--schedule", JSON.stringify(buildScheduleObject())
    ]
    updateProc.command = command
    updateProc.running = true
  }

  function deleteTask() {
    if (!selectedTask) return
    if (deleteProc.running) return
    deleteProc.command = ["python3", backendScriptPath(), "delete", "--id", String(selectedTask.id)]
    deleteProc.running = true
  }

  function selectedTaskFromList() {
    if (root.selectedListIndex < 0 || root.selectedListIndex >= root.tasks.length) return null
    return root.tasks[root.selectedListIndex]
  }

  function statusSummary(task) {
    if (!task || !task.lastStatus) return ""
    var status = String(task.lastStatus.status || "never")
    var message = String(task.lastStatus.message || "")
    return message !== "" ? status + " · " + message : status
  }

  Process {
    id: listProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var data = root.parseJson(text)
        if (!data || !data.tasks) {
          root.errorText = "Failed to read tasks."
          return
        }
        root.tasks = data.tasks
        root.ensureSelectedIndex()
      }
    }
    stderr: StdioCollector { id: listErr; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) root.errorText = String(listErr.text || "Failed to list tasks.")
    }
  }

  Process {
    id: actionProc
    stdout: StdioCollector { waitForEnd: true }
    stderr: StdioCollector { id: actionErr; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.errorText = String(actionErr.text || "Action failed.")
        return
      }
      root.errorText = ""
      root.refreshTasks()
      if (root.selectedTaskId !== "") {
        root.refreshStatus(root.selectedTaskId)
        root.refreshLog(root.selectedTaskId)
      }
    }
  }

  Process {
    id: addProc
    stdout: StdioCollector { waitForEnd: true }
    stderr: StdioCollector { id: addErr; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.errorText = String(addErr.text || "Failed to add task.")
        return
      }
      root.editorName = ""
      root.editorCommand = ""
      root.editorArguments = ""
      root.editorWorkingDirectory = ""
      root.editorTimeoutSeconds = 0
      root.editorAdvancedExpanded = false
      root.editorScheduleEnabled = false
      root.showingEditor = false
      root.editingTask = false
      root.errorText = ""
      root.refreshTasks()
    }
  }

  Process {
    id: updateProc
    stdout: StdioCollector { waitForEnd: true }
    stderr: StdioCollector { id: updateErr; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.errorText = String(updateErr.text || "Failed to update task.")
        return
      }
      root.showingEditor = false
      root.editingTask = false
      root.errorText = ""
      root.refreshTasks()
      if (root.selectedTaskId !== "") root.openDetails(root.selectedTaskId)
    }
  }

  Process {
    id: deleteProc
    stdout: StdioCollector { waitForEnd: true }
    stderr: StdioCollector { id: deleteErr; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.errorText = String(deleteErr.text || "Failed to delete task.")
        return
      }
      root.showingEditor = false
      root.editingTask = false
      root.confirmingDelete = false
      root.returnToEditorAfterDeleteCancel = false
      root.selectedTaskId = ""
      root.errorText = ""
      root.refreshTasks()
    }
  }

  Process {
    id: statusProc
    property string taskId: ""
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (statusProc.taskId !== root.selectedTaskId) return
        var data = root.parseJson(text)
        if (!data) return
        if (data.running === true) {
          root.detailsStatusText = "running"
          root.detailsNextRunText = data.nextRun ? "Next run: " + String(data.nextRun) : ""
          return
        }
        if (!data.lastStatus) return
        var s = data.lastStatus
        var summary = String(s.status || "never")
        if (s.message) summary = summary + " · " + String(s.message)
        if (s.durationMs !== undefined && s.durationMs !== null) {
          summary = summary + " · " + String(Math.round(Number(s.durationMs) / 1000)) + "s"
        }
        root.detailsStatusText = summary
        root.detailsNextRunText = data.nextRun ? "Next run: " + String(data.nextRun) : ""
      }
    }
    stderr: StdioCollector { id: statusErr; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) root.errorText = String(statusErr.text || "Failed to load status.")
    }
  }

  Process {
    id: logProc
    property string taskId: ""
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (logProc.taskId !== root.selectedTaskId) return
        var data = root.parseJson(text)
        if (!data) return
        root.detailsLogText = String(data.text || "")
      }
    }
    stderr: StdioCollector { id: logErr; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) root.errorText = String(logErr.text || "Failed to load log.")
    }
  }

  Timer {
    interval: 1000
    repeat: true
    running: root.opened && !root.showingEditor && root.selectedTaskId !== ""
    onTriggered: {
      root.refreshTasks()
      root.refreshStatus(root.selectedTaskId)
      root.refreshLog(root.selectedTaskId)
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(620))
    contentHeight: panel.fittedContentHeight(
      root.showingEditor ? Style.space(650)
      : root.selectedTaskId !== "" ? Style.space(650)
      : Math.max(Style.space(150), Math.min(Style.space(500), content.implicitHeight)))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      focus: true
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Escape) {
          event.accepted = true
          if (root.confirmingDelete) {
            root.cancelDeleteConfirmation()
            return
          }
          if (root.showingEditor) {
            root.showingEditor = false
            root.editingTask = false
            return
          }
          if (root.selectedTaskId !== "") {
            root.selectedTaskId = ""
            root.refreshTasks()
            return
          }
          root.close()
          return
        }

        if (root.showingEditor) return
        if (root.selectedTaskId !== "") {
          if (event.key === Qt.Key_E && root.selectedTask) {
            event.accepted = true
            root.openEditEditor(root.selectedTask)
          }
          return
        }
        if (event.key === Qt.Key_N || event.key === Qt.Key_A) {
          event.accepted = true
          root.openAddEditor()
          return
        }
        if (!root.tasks || root.tasks.length === 0) return

        if (event.key === Qt.Key_Down) {
          event.accepted = true
          if (root.selectedListIndex < root.tasks.length - 1) root.selectedListIndex += 1
          return
        }
        if (event.key === Qt.Key_Up) {
          event.accepted = true
          if (root.selectedListIndex > 0) root.selectedListIndex -= 1
          return
        }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
          event.accepted = true
          var selected = root.selectedTaskFromList()
          if (selected) root.openDetails(String(selected.id))
          return
        }
        if (event.key === Qt.Key_Space) {
          event.accepted = true
          var selectedTask = root.selectedTaskFromList()
          if (!selectedTask) return
          if (selectedTask.running === true) root.runAction("stop", String(selectedTask.id))
          else root.runAction("run", String(selectedTask.id))
        }
      }

      Flickable {
        id: contentScroll
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

        Column {
          id: content
          x: Style.space(2)
          width: Math.max(1, contentScroll.width - Style.space(4))
          spacing: Style.space(8)

        Item {
          width: parent.width
          implicitHeight: Math.max(title.implicitHeight, addTaskButton.implicitHeight)
          height: implicitHeight

          Text {
            id: title
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: "OmaRun"
            color: root.barForeground
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            font.pixelSize: Style.font.subtitle
            font.bold: true
          }

          Text {
            id: addTaskButton
            width: Style.space(56)
            height: Style.space(24)
            x: Math.max(0, parent.width - width)
            y: Math.max(0, (parent.height - height) / 2)
            text: "+ Add"
            color: root.barForeground
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            font.pixelSize: Style.font.body
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter

            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.PointingHandCursor
              onClicked: root.openAddEditor()
            }
          }
        }

        Text {
          visible: root.errorText !== ""
          width: parent.width
          wrapMode: Text.WordWrap
          color: root.barForeground
          opacity: 0.85
          text: root.errorText
        }

        Components.TaskEditor {
          id: taskEditor
          visible: root.showingEditor && !root.confirmingDelete
          width: parent.width
          foregroundColor: root.barForeground
          mode: root.editingTask ? "edit" : "add"
          taskId: root.selectedTask ? String(root.selectedTask.id || "") : ""
          name: root.editorName
          command: root.editorCommand
          arguments: root.editorArguments
          workingDirectory: root.editorWorkingDirectory
          timeoutSeconds: root.editorTimeoutSeconds
          advancedExpanded: root.editorAdvancedExpanded
          scheduleEnabled: root.editorScheduleEnabled
          scheduleMode: root.editorScheduleMode
          scheduleInterval: root.editorScheduleInterval
          scheduleTime: root.editorScheduleTime
          scheduleWeekdays: root.editorScheduleWeekdays
          onNameChanged: root.editorName = name
          onCommandChanged: root.editorCommand = command
          onArgumentsChanged: root.editorArguments = arguments
          onWorkingDirectoryChanged: root.editorWorkingDirectory = workingDirectory
          onTimeoutSecondsChanged: root.editorTimeoutSeconds = timeoutSeconds
          onAdvancedExpandedChanged: root.editorAdvancedExpanded = advancedExpanded
          onScheduleEnabledChanged: root.editorScheduleEnabled = scheduleEnabled
          onScheduleModeChanged: root.editorScheduleMode = scheduleMode
          onScheduleIntervalChanged: root.editorScheduleInterval = scheduleInterval
          onScheduleTimeChanged: root.editorScheduleTime = scheduleTime
          onScheduleWeekdaysChanged: root.editorScheduleWeekdays = scheduleWeekdays
          onCancelRequested: {
            root.showingEditor = false
            root.editingTask = false
            root.confirmingDelete = false
            root.returnToEditorAfterDeleteCancel = false
            root.errorText = ""
          }
          onDeleteRequested: root.requestDelete(root.selectedTask, true)
          onSaveRequested: {
            if (root.editingTask) root.updateTask()
            else root.addTask()
          }
        }

        Rectangle {
          visible: root.showingEditor && root.editingTask && root.confirmingDelete
          width: parent.width
          implicitHeight: deleteConfirmationContent.implicitHeight + Style.space(24)
          height: visible ? implicitHeight : 0
          radius: Style.cornerRadius
          color: Style.normalFillFor(root.barForeground, Color.accent, Color.urgent)
          border.width: Math.max(1, Style.normalBorderWidth)
          border.color: Color.urgent

          Column {
            id: deleteConfirmationContent
            x: Style.space(12)
            y: Style.space(12)
            width: Math.max(1, parent.width - Style.space(24))
            spacing: Style.space(10)

            Text {
              width: parent.width
              text: "Delete \u201c" + String(root.selectedTask ? root.selectedTask.name : "this task") + "\u201d?"
              color: root.barForeground
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.subtitle
              font.bold: true
              wrapMode: Text.WordWrap
            }

            Text {
              width: parent.width
              text: "The saved command, schedule, and run history will be removed. The script file itself will not be deleted."
              color: root.barForeground
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.bodySmall
              wrapMode: Text.WordWrap
              opacity: 0.72
            }

            Row {
              spacing: Style.space(8)

              Button {
                height: Style.spacing.controlHeight
                text: "Cancel"
                bordered: true
                foreground: root.barForeground
                onClicked: root.cancelDeleteConfirmation()
              }

              Button {
                height: Style.spacing.controlHeight
                text: "Delete task"
                iconText: "\u2715"
                bordered: true
                foreground: Color.urgent
                onClicked: root.deleteTask()
              }
            }
          }
        }

        Column {
          visible: !root.showingEditor
          width: parent.width
          height: visible ? implicitHeight : 0
          spacing: 4

          Text {
            visible: root.tasks.length === 0
            width: Style.space(130)
            height: Style.space(24)
            text: "No commands yet"
            color: root.barForeground
            opacity: 0.8
          }

          Text {
            visible: root.tasks.length === 0
            text: "+ Add a command"
            color: root.barForeground
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter

            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.PointingHandCursor
              onClicked: root.openAddEditor()
            }
          }

          Repeater {
            model: root.tasks
            delegate: Column {
              id: taskDelegate
              required property var modelData
              required property int index
              width: parent.width
              height: implicitHeight
              spacing: expanded ? Style.space(10) : 0
              readonly property bool expanded: String(modelData.id || "") === root.selectedTaskId

              Components.TaskRow {
                width: parent.width
                foregroundColor: root.barForeground
                taskId: String(taskDelegate.modelData.id || "")
                name: String(taskDelegate.modelData.name || "")
                status: String((taskDelegate.modelData.lastStatus && taskDelegate.modelData.lastStatus.status) || "never")
                secondaryText: root.statusSummary(taskDelegate.modelData)
                scheduled: taskDelegate.modelData.schedule && taskDelegate.modelData.schedule.enabled === true
                running: taskDelegate.modelData.running === true
                selected: taskDelegate.index === root.selectedListIndex
                expanded: taskDelegate.expanded
                onRunRequested: function(taskId) {
                  root.selectedListIndex = taskDelegate.index
                  root.openDetails(taskId)
                  root.runAction("run", taskId)
                }
                onStopRequested: function(taskId) {
                  root.selectedListIndex = taskDelegate.index
                  root.openDetails(taskId)
                  root.runAction("stop", taskId)
                }
                onOpenDetailsRequested: function(taskId) {
                  root.selectedListIndex = taskDelegate.index
                  root.toggleDetails(taskId)
                }
              }

              Components.TaskDetails {
                visible: taskDelegate.expanded
                width: parent.width
                inlineMode: true
                foregroundColor: root.barForeground
                taskId: String(taskDelegate.modelData.id || "")
                name: String(taskDelegate.modelData.name || "")
                commandText: String(taskDelegate.modelData.command || "")
                  + (String(taskDelegate.modelData.arguments || "") !== "" ? " " + String(taskDelegate.modelData.arguments) : "")
                running: taskDelegate.modelData.running === true
                status: String((taskDelegate.modelData.lastStatus && taskDelegate.modelData.lastStatus.status) || "never")
                statusText: root.detailsStatusText
                nextRunText: root.detailsNextRunText
                logText: root.detailsLogText
                onEditRequested: root.openEditEditor(taskDelegate.modelData)
                onDeleteRequested: root.requestDelete(taskDelegate.modelData, false)
              }
            }
          }
        }
      }
      }
    }
  }
}
