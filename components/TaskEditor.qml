import QtQuick
import qs.Commons

Item {
  id: root
  property string mode: "add"
  property string taskId: ""
  property string name: ""
  property string command: ""
  property string arguments: ""
  property string workingDirectory: ""
  property int timeoutSeconds: 0
  property bool scheduleEnabled: false
  property bool advancedExpanded: false
  property string scheduleMode: "every-hours"
  property int scheduleInterval: 6
  property string scheduleTime: "03:00"
  property var scheduleWeekdays: []

  signal saveRequested()
  signal cancelRequested()
  signal deleteRequested()

  function hasWeekday(day) {
    for (var i = 0; i < root.scheduleWeekdays.length; i++) {
      if (Number(root.scheduleWeekdays[i]) === day) return true
    }
    return false
  }

  function toggleWeekday(day) {
    var out = []
    var found = false
    for (var i = 0; i < root.scheduleWeekdays.length; i++) {
      var value = Number(root.scheduleWeekdays[i])
      if (value === day) found = true
      else out.push(value)
    }
    if (!found) out.push(day)
    root.scheduleWeekdays = out
  }

  Column {
    anchors.fill: parent
    spacing: Style.space(8)

    Text { text: root.mode === "edit" ? "Edit command" : "New command"; font.bold: true }

    Text { text: "Name" }
    Rectangle {
      width: parent.width
      height: Style.space(28)
      border.width: 1
      color: "transparent"
      TextInput {
        anchors.fill: parent
        anchors.margins: Style.space(6)
        text: root.name
        onTextChanged: root.name = text
      }
    }

    Text { text: "Command" }
    Rectangle {
      width: parent.width
      height: Style.space(28)
      border.width: 1
      color: "transparent"
      TextInput {
        anchors.fill: parent
        anchors.margins: Style.space(6)
        text: root.command
        onTextChanged: root.command = text
      }
    }

    Row {
      spacing: Style.space(8)
      Text { text: "Run automatically" }
      Rectangle {
        width: 24
        height: 20
        border.width: 1
        color: "transparent"
        Text { anchors.centerIn: parent; text: root.scheduleEnabled ? "●" : "○" }
        MouseArea {
          anchors.fill: parent
          onClicked: root.scheduleEnabled = !root.scheduleEnabled
        }
      }
    }

    Row {
      spacing: Style.space(8)
      Text { text: root.advancedExpanded ? "▾ Advanced" : "▸ Advanced" }
      MouseArea {
        anchors.fill: parent
        onClicked: root.advancedExpanded = !root.advancedExpanded
      }
    }

    Column {
      visible: root.advancedExpanded
      width: parent.width
      spacing: Style.space(8)

      Text { text: "Arguments" }
      Rectangle {
        width: parent.width
        height: Style.space(28)
        border.width: 1
        color: "transparent"
        TextInput {
          anchors.fill: parent
          anchors.margins: Style.space(6)
          text: root.arguments
          onTextChanged: root.arguments = text
        }
      }

      Text { text: "Working directory" }
      Rectangle {
        width: parent.width
        height: Style.space(28)
        border.width: 1
        color: "transparent"
        TextInput {
          anchors.fill: parent
          anchors.margins: Style.space(6)
          text: root.workingDirectory
          onTextChanged: root.workingDirectory = text
        }
      }

      Text { text: "Timeout (seconds, 0 = none)" }
      Rectangle {
        width: parent.width
        height: Style.space(28)
        border.width: 1
        color: "transparent"
        TextInput {
          anchors.fill: parent
          anchors.margins: Style.space(6)
          text: String(root.timeoutSeconds)
          inputMethodHints: Qt.ImhDigitsOnly
          onTextChanged: {
            var n = parseInt(text, 10)
            root.timeoutSeconds = isFinite(n) && n >= 0 ? n : 0
          }
        }
      }
    }

    Column {
      visible: root.scheduleEnabled
      spacing: Style.space(6)
      width: parent.width

      Text { text: "Mode" }
      Row {
        spacing: Style.space(6)
        Repeater {
          model: [
            "every-minutes",
            "every-hours",
            "every-days",
            "daily-at",
            "weekly"
          ]
          delegate: Rectangle {
            width: 94
            height: 22
            border.width: root.scheduleMode === modelData ? 2 : 1
            color: "transparent"
            Text {
              anchors.centerIn: parent
              text: String(modelData).replace("every-", "Every ").replace("-at", " at")
              font.pixelSize: 11
            }
            MouseArea {
              anchors.fill: parent
              onClicked: root.scheduleMode = modelData
            }
          }
        }
      }

      Column {
        visible: root.scheduleMode === "every-minutes" || root.scheduleMode === "every-hours" || root.scheduleMode === "every-days"
        spacing: Style.space(4)
        Text { text: "Interval" }
        Rectangle {
          width: 80
          height: Style.space(24)
          border.width: 1
          color: "transparent"
          TextInput {
            anchors.fill: parent
            anchors.margins: Style.space(6)
            text: String(root.scheduleInterval)
            inputMethodHints: Qt.ImhDigitsOnly
            onTextChanged: {
              var n = parseInt(text, 10)
              root.scheduleInterval = isFinite(n) && n > 0 ? n : 1
            }
          }
        }
      }

      Column {
        visible: root.scheduleMode === "daily-at" || root.scheduleMode === "weekly"
        spacing: Style.space(4)
        Text { text: "Time (HH:MM)" }
        Rectangle {
          width: 90
          height: Style.space(24)
          border.width: 1
          color: "transparent"
          TextInput {
            anchors.fill: parent
            anchors.margins: Style.space(6)
            text: root.scheduleTime
            onTextChanged: root.scheduleTime = text
          }
        }
      }

      Row {
        visible: root.scheduleMode === "weekly"
        spacing: Style.space(4)
        Repeater {
          model: ["M", "T", "W", "T", "F", "S", "S"]
          delegate: Rectangle {
            width: 22
            height: 22
            border.width: root.hasWeekday(index) ? 2 : 1
            color: "transparent"
            Text { anchors.centerIn: parent; text: modelData; font.pixelSize: 11 }
            MouseArea {
              anchors.fill: parent
              onClicked: root.toggleWeekday(index)
            }
          }
        }
      }
    }

    Row {
      spacing: Style.space(8)
      Rectangle {
        width: 64
        height: 24
        border.width: 1
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: "Cancel" }
        MouseArea {
          anchors.fill: parent
          onClicked: root.cancelRequested()
        }
      }
      Rectangle {
        width: root.mode === "edit" ? 60 : 48
        height: 24
        border.width: 1
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: root.mode === "edit" ? "Save" : "Add" }
        MouseArea {
          anchors.fill: parent
          onClicked: root.saveRequested()
        }
      }
      Rectangle {
        visible: root.mode === "edit"
        width: 64
        height: 24
        border.width: 1
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: "Delete" }
        MouseArea {
          anchors.fill: parent
          onClicked: root.deleteRequested()
        }
      }
    }
  }
}
