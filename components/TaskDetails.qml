import QtQuick
import qs.Commons

Item {
  id: root
  property string taskId: ""
  property string name: ""
  property string statusText: ""
  property string logText: ""
  property string nextRunText: ""
  property bool running: false

  signal backRequested()
  signal runRequested()
  signal stopRequested()
  signal editRequested()
  signal deleteRequested()

  Column {
    anchors.fill: parent
    spacing: Style.space(8)

    Row {
      spacing: Style.space(8)
      Text { text: "←"; font.bold: true }
      Text { text: root.name; font.bold: true }

      MouseArea {
        anchors.fill: parent
        onClicked: root.backRequested()
      }
    }

    Text { text: root.statusText; wrapMode: Text.Wrap }
    Text { text: root.nextRunText; visible: root.nextRunText !== "" }

    Row {
      spacing: Style.space(8)
      Rectangle {
        width: 64
        height: 24
        border.width: 1
        radius: 4
        color: "transparent"

        Text {
          anchors.centerIn: parent
          text: root.running ? "Stop" : "Run"
        }
        MouseArea {
          anchors.fill: parent
          onClicked: {
            if (root.running) root.stopRequested()
            else root.runRequested()
          }
        }
      }

      Rectangle {
        width: 56
        height: 24
        border.width: 1
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: "Edit" }
        MouseArea {
          anchors.fill: parent
          onClicked: root.editRequested()
        }
      }

      Rectangle {
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

    Text {
      text: root.logText
      wrapMode: Text.WrapAnywhere
      width: parent.width
    }
  }
}
