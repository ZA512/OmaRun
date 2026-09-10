import QtQuick
import qs.Commons

Item {
  id: root
  implicitHeight: editorContent.implicitHeight
  height: visible ? implicitHeight : 0
  property color foregroundColor: "white"
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
    id: editorContent
    width: parent.width
    spacing: Style.space(8)

    Text { text: root.mode === "edit" ? "Edit command" : "New command"; color: root.foregroundColor; font.bold: true }

    Text { text: "Name"; color: root.foregroundColor }
    Rectangle {
      width: parent.width
      height: Style.space(28)
      border.width: 1
      border.color: root.foregroundColor
      color: "transparent"
      TextInput {
        anchors.fill: parent
        anchors.margins: Style.space(6)
        text: root.name
        color: root.foregroundColor
        onTextChanged: root.name = text
      }
    }

    Text { text: "Command"; color: root.foregroundColor }
    Rectangle {
      width: parent.width
      height: Style.space(28)
      border.width: 1
      border.color: root.foregroundColor
      color: "transparent"
      TextInput {
        anchors.fill: parent
        anchors.margins: Style.space(6)
        text: root.command
        color: root.foregroundColor
        onTextChanged: root.command = text
      }
    }

    Row {
      spacing: Style.space(8)
      Text { text: "Run automatically"; color: root.foregroundColor }
      Rectangle {
        width: 24
        height: 20
        border.width: 1
        border.color: root.foregroundColor
        color: "transparent"
        Text { anchors.centerIn: parent; text: root.scheduleEnabled ? "●" : "○"; color: root.foregroundColor }
        MouseArea {
          anchors.fill: parent
          onClicked: root.scheduleEnabled = !root.scheduleEnabled
        }
      }
    }

    Row {
      spacing: Style.space(8)
      Text { text: root.advancedExpanded ? "▾ Advanced" : "▸ Advanced"; color: root.foregroundColor }
      TapHandler {
        onTapped: root.advancedExpanded = !root.advancedExpanded
      }
    }

    Column {
      visible: root.advancedExpanded
      width: parent.width
      spacing: Style.space(8)

      Text { text: "Arguments"; color: root.foregroundColor }
      Rectangle {
        width: parent.width
        height: Style.space(28)
        border.width: 1
        border.color: root.foregroundColor
        color: "transparent"
        TextInput {
          anchors.fill: parent
          anchors.margins: Style.space(6)
          text: root.arguments
          color: root.foregroundColor
          onTextChanged: root.arguments = text
        }
      }

      Text { text: "Working directory"; color: root.foregroundColor }
      Rectangle {
        width: parent.width
        height: Style.space(28)
        border.width: 1
        border.color: root.foregroundColor
        color: "transparent"
        TextInput {
          anchors.fill: parent
          anchors.margins: Style.space(6)
          text: root.workingDirectory
          color: root.foregroundColor
          onTextChanged: root.workingDirectory = text
        }
      }

      Text { text: "Timeout (seconds, 0 = none)"; color: root.foregroundColor }
      Rectangle {
        width: parent.width
        height: Style.space(28)
        border.width: 1
        border.color: root.foregroundColor
        color: "transparent"
        TextInput {
          anchors.fill: parent
          anchors.margins: Style.space(6)
          text: String(root.timeoutSeconds)
          color: root.foregroundColor
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

      Text { text: "Mode"; color: root.foregroundColor }
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
            border.color: root.foregroundColor
            color: "transparent"
            Text {
              anchors.centerIn: parent
              text: String(modelData).replace("every-", "Every ").replace("-at", " at")
              color: root.foregroundColor
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
        Text { text: "Interval"; color: root.foregroundColor }
        Rectangle {
          width: 80
          height: Style.space(24)
          border.width: 1
          border.color: root.foregroundColor
          color: "transparent"
          TextInput {
            anchors.fill: parent
            anchors.margins: Style.space(6)
            text: String(root.scheduleInterval)
            color: root.foregroundColor
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
        Text { text: "Time (HH:MM)"; color: root.foregroundColor }
        Rectangle {
          width: 90
          height: Style.space(24)
          border.width: 1
          border.color: root.foregroundColor
          color: "transparent"
          TextInput {
            anchors.fill: parent
            anchors.margins: Style.space(6)
            text: root.scheduleTime
            color: root.foregroundColor
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
            border.color: root.foregroundColor
            color: "transparent"
            Text { anchors.centerIn: parent; text: modelData; color: root.foregroundColor; font.pixelSize: 11 }
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
        border.color: root.foregroundColor
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: "Cancel"; color: root.foregroundColor }
        MouseArea {
          anchors.fill: parent
          onClicked: root.cancelRequested()
        }
      }
      Rectangle {
        width: root.mode === "edit" ? 60 : 48
        height: 24
        border.width: 1
        border.color: root.foregroundColor
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: root.mode === "edit" ? "Save" : "Add"; color: root.foregroundColor }
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
        border.color: root.foregroundColor
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: "Delete"; color: root.foregroundColor }
        MouseArea {
          anchors.fill: parent
          onClicked: root.deleteRequested()
        }
      }
    }
  }
}
