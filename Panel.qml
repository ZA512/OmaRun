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
    selectedTaskId = taskId
    showingEditor = false
    refreshStatus(taskId)
    refreshLog(taskId)
  }

  function openAddEditor() {
    editingTask = false
    showingEditor = true
    confirmingDelete = false
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
  }

  function openEditEditor(task) {
    if (!task) return
    editingTask = true
    showingEditor = true
    confirmingDelete = false
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
  }

  function refreshStatus(taskId) {
    if (statusProc.running) statusProc.running = false
    statusProc.command = ["python3", backendScriptPath(), "status", "--id", taskId]
    statusProc.running = true
  }

  function refreshLog(taskId) {
    if (logProc.running) logProc.running = false
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
      root.selectedTaskId = ""
      root.errorText = ""
      root.refreshTasks()
    }
  }

  Process {
    id: statusProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var data = root.parseJson(text)
        if (!data || !data.lastStatus) return
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
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
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

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(480))
    contentHeight: panel.fittedContentHeight(
      root.showingEditor ? Style.space(560)
      : root.selectedTaskId !== "" ? Style.space(420)
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
            root.confirmingDelete = false
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

        if (root.showingEditor || root.selectedTaskId !== "") return
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
        contentWidth: content.width
        contentHeight: content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

        Column {
          id: content
          width: Math.max(1, panel.contentWidth - panel.padding * 2 - Style.space(2))
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
          visible: root.showingEditor
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
            root.errorText = ""
          }
          onDeleteRequested: root.confirmingDelete = true
          onSaveRequested: {
            if (root.editingTask) root.updateTask()
            else root.addTask()
          }
        }

        Column {
          visible: root.showingEditor && root.editingTask && root.confirmingDelete
          width: parent.width
          height: visible ? implicitHeight : 0
          spacing: 6
          Text { text: "Delete this task? Script source file will not be deleted."; wrapMode: Text.WordWrap }
          Row {
            spacing: 8
            Rectangle {
              width: 64; height: 24; border.width: 1; radius: 4; color: "transparent"
              Text { anchors.centerIn: parent; text: "Cancel" }
              MouseArea { anchors.fill: parent; onClicked: root.confirmingDelete = false }
            }
            Rectangle {
              width: 64; height: 24; border.width: 1; radius: 4; color: "transparent"
              Text { anchors.centerIn: parent; text: "Delete" }
              MouseArea { anchors.fill: parent; onClicked: root.deleteTask() }
            }
          }
        }

        Components.TaskDetails {
          visible: !root.showingEditor && root.selectedTaskId !== "" && root.selectedTask
          width: parent.width
          foregroundColor: root.barForeground
          taskId: root.selectedTask ? String(root.selectedTask.id || "") : ""
          name: root.selectedTask ? String(root.selectedTask.name || "") : ""
          commandText: root.selectedTask
            ? String(root.selectedTask.command || "")
              + (String(root.selectedTask.arguments || "") !== "" ? " " + String(root.selectedTask.arguments) : "")
            : ""
          running: root.selectedTask ? root.selectedTask.running === true : false
          statusText: root.detailsStatusText
          nextRunText: root.detailsNextRunText
          logText: root.detailsLogText
          onBackRequested: root.selectedTaskId = ""
          onRunRequested: if (root.selectedTask) root.runAction("run", root.selectedTask.id)
          onStopRequested: if (root.selectedTask) root.runAction("stop", root.selectedTask.id)
          onEditRequested: root.openEditEditor(root.selectedTask)
          onDeleteRequested: {
            root.openEditEditor(root.selectedTask)
            root.confirmingDelete = true
          }
        }

        Column {
          visible: !root.showingEditor && root.selectedTaskId === ""
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
            delegate: Components.TaskRow {
              width: parent.width
              taskId: String(modelData.id || "")
              name: String(modelData.name || "")
              status: String((modelData.lastStatus && modelData.lastStatus.status) || "never")
              secondaryText: root.statusSummary(modelData)
              scheduled: modelData.schedule && modelData.schedule.enabled === true
              running: modelData.running === true
              selected: index === root.selectedListIndex
              onRunRequested: function(taskId) { root.runAction("run", taskId) }
              onStopRequested: function(taskId) { root.runAction("stop", taskId) }
              onOpenDetailsRequested: function(taskId) {
                root.selectedListIndex = index
                root.openDetails(taskId)
              }
            }
          }
        }
      }
      }
    }
  }
}
