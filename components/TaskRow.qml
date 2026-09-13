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
  property bool expanded: false

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

  Item {
    anchors.fill: parent

    Text {
      id: chevron
      text: root.expanded ? "▾" : "▸"
      color: root.foregroundColor
      width: Style.space(12)
      anchors.left: parent.left
      anchors.verticalCenter: parent.verticalCenter
      horizontalAlignment: Text.AlignHCenter
    }

    Text {
      id: statusIcon
      text: root.running ? "◉" : (root.status === "success" ? "●" : (root.status === "failed" ? "✕" : "○"))
      color: root.running ? Color.accent
        : (root.status === "failed" ? Color.urgent
        : (root.status === "success" ? Color.accent : root.foregroundColor))
      anchors.left: chevron.right
      anchors.leftMargin: Style.space(8)
      anchors.verticalCenter: parent.verticalCenter
    }
    Text {
      id: taskName
      text: root.name
      color: root.foregroundColor
      elide: Text.ElideRight
      anchors.left: statusIcon.right
      anchors.leftMargin: Style.space(8)
      anchors.right: secondary.left
      anchors.rightMargin: Style.space(8)
      anchors.verticalCenter: parent.verticalCenter
    }
    Text {
      id: secondary
      text: root.secondaryText
      color: root.foregroundColor
      width: Style.space(140)
      elide: Text.ElideRight
      visible: !root.expanded && (root.selected || hitArea.containsMouse)
      opacity: 0.75
      anchors.right: scheduleIcon.left
      anchors.rightMargin: Style.space(8)
      anchors.verticalCenter: parent.verticalCenter
    }
    Text {
      id: scheduleIcon
      text: root.scheduled ? "⏱" : ""
      color: root.foregroundColor
      width: Style.space(16)
      anchors.right: runButton.left
      anchors.rightMargin: Style.space(8)
      anchors.verticalCenter: parent.verticalCenter
    }

    Rectangle {
      id: runButton
      width: Style.space(48)
      height: Style.space(22)
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
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
        onClicked: function(mouse) {
          mouse.accepted = true
          if (root.running) root.stopRequested(root.taskId)
          else root.runRequested(root.taskId)
        }
      }
    }
  }
}
