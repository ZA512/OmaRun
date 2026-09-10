import QtQuick
import qs.Commons

Item {
  id: root
  property color foregroundColor: "white"
  property string taskId: ""
  property string name: ""
  property string status: "never"
  property string secondaryText: ""
  property bool scheduled: false
  property bool running: false
  property bool selected: false

  signal runRequested(string taskId)
  signal stopRequested(string taskId)
  signal openDetailsRequested(string taskId)

  width: parent ? parent.width : 320
  height: Style.space(30)

  MouseArea {
    id: hitArea
    anchors.fill: parent
    hoverEnabled: true
    onClicked: root.openDetailsRequested(root.taskId)
  }

  Row {
    anchors.fill: parent
    spacing: Style.space(8)

    Text { text: root.selected ? "›" : " "; color: root.foregroundColor; width: 8 }

    Text {
      text: root.running ? "◉" : (root.status === "success" ? "●" : (root.status === "failed" ? "✕" : "○"))
      color: root.foregroundColor
    }
    Text { text: root.name; color: root.foregroundColor; elide: Text.ElideRight; width: 210 }
    Text {
      text: root.secondaryText
      color: root.foregroundColor
      width: 88
      elide: Text.ElideRight
      visible: root.selected || hitArea.containsMouse
      opacity: 0.75
    }
    Text { text: root.scheduled ? "⏱" : ""; color: root.foregroundColor; width: 16 }

    Rectangle {
      width: 44
      height: 22
      radius: 4
      color: "transparent"
      border.width: 1
      border.color: root.foregroundColor

      Text {
        anchors.centerIn: parent
        text: root.running ? "Stop" : "Run"
        color: root.foregroundColor
      }

      MouseArea {
        anchors.fill: parent
        onClicked: {
          mouse.accepted = true
          if (root.running) root.stopRequested(root.taskId)
          else root.runRequested(root.taskId)
        }
      }
    }
  }
}
