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
  property string status: "never"
  property bool running: false
  property bool inlineMode: false

  readonly property color statusColor: root.running ? Color.accent
    : (root.status === "failed" ? Color.urgent
    : (root.status === "success" ? Color.accent : Color.muted))

  signal backRequested()
  signal runRequested()
  signal stopRequested()
  signal editRequested()
  signal deleteRequested()

  Column {
    id: detailsContent
    width: parent.width
    spacing: Style.space(10)

    Item {
      visible: !root.inlineMode
      width: parent.width
      height: visible ? Style.space(30) : 0

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
      height: Style.spacing.controlHeight
      spacing: Style.space(8)

      Button {
        visible: !root.inlineMode
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

    Rectangle {
      width: parent.width
      implicitHeight: statusContent.implicitHeight + Style.space(20)
      height: implicitHeight
      radius: Style.cornerRadius
      color: Style.normalFillFor(root.foregroundColor, Color.accent, Color.urgent)
      border.width: Math.max(1, Style.normalBorderWidth)
      border.color: Style.normalBorderFor(root.foregroundColor, Color.accent, Color.urgent)

      Column {
        id: statusContent
        x: Style.space(10)
        y: Style.space(10)
        width: Math.max(1, parent.width - Style.space(20))
        spacing: Style.space(5)

        Row {
          width: parent.width
          spacing: Style.space(7)

          Rectangle {
            width: Style.space(8)
            height: width
            radius: width / 2
            color: root.statusColor
            anchors.verticalCenter: parent.verticalCenter
          }

          Text {
            width: Math.max(1, parent.width - Style.space(15))
            text: root.statusText || "Never executed"
            color: root.foregroundColor
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            font.bold: true
            wrapMode: Text.WordWrap
          }
        }

        Text {
          visible: root.nextRunText !== ""
          width: parent.width
          text: root.nextRunText
          color: root.foregroundColor
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
          opacity: 0.65
        }
      }
    }

    Column {
      width: parent.width
      height: implicitHeight
      spacing: Style.space(5)

      Text {
        text: "COMMAND"
        color: root.foregroundColor
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
        opacity: 0.55
      }

      Rectangle {
        width: parent.width
        implicitHeight: commandLabel.implicitHeight + Style.space(16)
        height: implicitHeight
        radius: Style.cornerRadius
        color: Style.normalFillFor(root.foregroundColor, Color.accent, Color.urgent)
        border.width: Math.max(1, Style.normalBorderWidth)
        border.color: Style.normalBorderFor(root.foregroundColor, Color.accent, Color.urgent)

        Text {
          id: commandLabel
          x: Style.space(9)
          y: Style.space(8)
          width: Math.max(1, parent.width - Style.space(18))
          text: root.commandText
          color: root.foregroundColor
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WrapAnywhere
          opacity: 0.9
        }
      }
    }

    LogViewer {
      width: parent.width
      height: Style.space(300)
      foregroundColor: root.foregroundColor
      title: root.running ? "LIVE OUTPUT" : "LAST OUTPUT"
      text: root.logText
      emptyText: root.running ? "Waiting for output…" : "No output was produced by the last run."
      live: root.running
    }
  }
}
