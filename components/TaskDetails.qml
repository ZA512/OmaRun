import QtQuick
import qs.Commons

Item {
  id: root
  implicitHeight: detailsContent.implicitHeight
  property color foregroundColor: "white"
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
    id: detailsContent
    width: parent.width
    spacing: Style.space(8)

    Row {
      spacing: Style.space(8)
      Text { text: "←"; color: root.foregroundColor; font.bold: true }
      Text { text: root.name; color: root.foregroundColor; font.bold: true }

      MouseArea {
        anchors.fill: parent
        onClicked: root.backRequested()
      }
    }

    Text { text: root.statusText; color: root.foregroundColor; wrapMode: Text.Wrap }
    Text { text: root.nextRunText; color: root.foregroundColor; visible: root.nextRunText !== "" }

    Row {
      spacing: Style.space(8)
      Rectangle {
        width: 64
        height: 24
        border.width: 1
        border.color: root.foregroundColor
        radius: 4
        color: "transparent"

        Text {
          anchors.centerIn: parent
          text: root.running ? "Stop" : "Run"
          color: root.foregroundColor
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
        border.color: root.foregroundColor
        radius: 4
        color: "transparent"
        Text { anchors.centerIn: parent; text: "Edit"; color: root.foregroundColor }
        MouseArea {
          anchors.fill: parent
          onClicked: root.editRequested()
        }
      }

      Rectangle {
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

    Text {
      text: root.logText
      color: root.foregroundColor
      wrapMode: Text.WrapAnywhere
      width: parent.width
    }
  }
}
