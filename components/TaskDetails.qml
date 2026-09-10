import QtQuick
import qs.Commons
import qs.Ui

Item {
  id: root
  implicitHeight: detailsContent.implicitHeight
  height: visible ? implicitHeight : 0

  property color foregroundColor: "white"
  property string taskId: ""
  property string name: ""
  property string commandText: ""
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
    spacing: Style.space(12)

    Item {
      width: parent.width
      height: Style.space(30)

      Button {
        width: Style.space(32)
        height: Style.space(28)
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        text: "←"
        foreground: root.foregroundColor
        horizontalPadding: 0
        verticalPadding: 0
        onClicked: root.backRequested()
      }

      Text {
        anchors.left: parent.left
        anchors.leftMargin: Style.space(42)
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        text: root.name
        color: root.foregroundColor
        font.family: Style.font.family
        font.pixelSize: Style.font.subtitle
        font.bold: true
        elide: Text.ElideRight
      }
    }

    Row {
      width: parent.width
      height: Style.space(30)
      spacing: Style.space(8)

      Button {
        width: Style.space(74)
        height: parent.height
        text: root.running ? "Stop" : "Run"
        iconText: root.running ? "■" : "▶"
        bordered: true
        foreground: root.foregroundColor
        onClicked: root.running ? root.stopRequested() : root.runRequested()
      }

      Button {
        width: Style.space(74)
        height: parent.height
        text: "Edit"
        bordered: true
        foreground: root.foregroundColor
        onClicked: root.editRequested()
      }

      Button {
        width: Style.space(86)
        height: parent.height
        text: "Delete"
        foreground: root.foregroundColor
        onClicked: root.deleteRequested()
      }
    }

    Column {
      width: parent.width
      height: implicitHeight
      spacing: Style.space(4)

      Text {
        text: "Status"
        color: root.foregroundColor
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
        opacity: 0.7
      }
      Text {
        width: parent.width
        text: root.statusText || "Never executed"
        color: root.foregroundColor
        font.family: Style.font.family
        wrapMode: Text.WordWrap
      }
      Text {
        visible: root.nextRunText !== ""
        width: parent.width
        text: root.nextRunText
        color: root.foregroundColor
        font.family: Style.font.family
        wrapMode: Text.WordWrap
        opacity: 0.8
      }
    }

    Column {
      width: parent.width
      height: implicitHeight
      spacing: Style.space(4)

      Text {
        text: "Command"
        color: root.foregroundColor
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
        opacity: 0.7
      }
      Text {
        width: parent.width
        text: root.commandText
        color: root.foregroundColor
        font.family: Style.font.family
        wrapMode: Text.WrapAnywhere
      }
    }

    Column {
      visible: root.logText !== ""
      width: parent.width
      height: visible ? implicitHeight : 0
      spacing: Style.space(4)

      Text {
        text: "Last output"
        color: root.foregroundColor
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
        opacity: 0.7
      }
      Text {
        width: parent.width
        text: root.logText
        color: root.foregroundColor
        font.family: Style.font.family
        wrapMode: Text.WrapAnywhere
        opacity: 0.85
      }
    }
  }
}
