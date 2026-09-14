import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.za512.omarun"

  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  readonly property bool popoutSwitchClosing: panelLoader.item
    ? panelLoader.item.popoutSwitchClosing === true
    : false
  property bool hasRunningTask: false
  property bool hasFailedScheduledTask: false

  function open() {
    refreshIndicator()
    if (panelLoader.item) panelLoader.item.open()
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close()
  }

  function toggle() {
    if (panelLoader.item) panelLoader.item.toggle()
  }

  function closeForPopoutSwitch() {
    if (panelLoader.item) panelLoader.item.closeForPopoutSwitch()
  }

  function injectPanel() {
    if (!panelLoader.item) return
    panelLoader.item.bar = root.bar
    panelLoader.item.anchorItem = button
    panelLoader.item.hostWidget = root
  }

  function backendScriptPath() {
    var resolved = Qt.resolvedUrl("backend/omarunctl.py").toString()
    if (resolved.indexOf("file://") === 0) return decodeURIComponent(resolved.substring(7))
    return resolved
  }

  function parseJson(raw) {
    try { return JSON.parse(String(raw || "")) } catch (e) { return null }
  }

  function refreshIndicator() {
    if (indicatorProc.running) return
    indicatorProc.command = ["python3", backendScriptPath(), "list"]
    indicatorProc.running = true
  }

  Process {
    id: indicatorProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var data = root.parseJson(text)
        if (!data || !data.tasks) return
        var running = false
        var failedScheduled = false
        for (var i = 0; i < data.tasks.length; i++) {
          var task = data.tasks[i]
          if (task.running === true) running = true
          var scheduled = task.schedule && task.schedule.enabled === true
          var status = task.lastStatus ? String(task.lastStatus.status || "") : ""
          if (scheduled && status === "failed") failedScheduled = true
        }
        root.hasRunningTask = running
        root.hasFailedScheduledTask = failedScheduled
      }
    }
  }

  Timer {
    interval: 15000
    running: true
    repeat: true
    onTriggered: root.refreshIndicator()
  }

  Component.onCompleted: refreshIndicator()

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onBarChanged: injectPanel()

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.hasFailedScheduledTask ? ">_ !" : (root.hasRunningTask ? ">_ •" : ">_")
    tooltipText: "Open OmaRun"
    onPressed: function(buttonCode) {
      if (buttonCode === Qt.LeftButton) root.toggle()
    }
  }
}
