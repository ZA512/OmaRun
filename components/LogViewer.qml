import QtQuick
import qs.Commons

Rectangle {
  id: root
  property string text: ""
  property string title: "OUTPUT"
  property string emptyText: "No output"
  property color foregroundColor: "white"
  property bool live: false

  implicitHeight: Style.space(300)
  radius: Style.cornerRadius
  color: Style.normalFillFor(root.foregroundColor, Color.accent, Color.urgent)
  border.width: Math.max(1, Style.normalBorderWidth)
  border.color: Style.normalBorderFor(root.foregroundColor, Color.accent, Color.urgent)

  Item {
    id: header
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    height: Style.space(34)

    Row {
      anchors.left: parent.left
      anchors.leftMargin: Style.space(10)
      anchors.verticalCenter: parent.verticalCenter
      spacing: Style.space(7)

      Rectangle {
        visible: root.live
        width: Style.space(7)
        height: width
        radius: width / 2
        color: Color.accent
        anchors.verticalCenter: parent.verticalCenter
      }

      Text {
        text: root.title
        color: root.foregroundColor
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
        opacity: 0.65
      }
    }
  }

  Rectangle {
    id: divider
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: header.bottom
    height: 1
    color: root.foregroundColor
    opacity: 0.14
  }

  Flickable {
    id: outputFlick
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: divider.bottom
    anchors.bottom: parent.bottom
    anchors.margins: Math.max(1, root.border.width)
    contentWidth: width
    contentHeight: Math.max(height, outputText.implicitHeight + Style.space(20))
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    TextEdit {
      id: outputText
      x: Style.space(10)
      y: Style.space(10)
      width: Math.max(1, outputFlick.width - Style.space(24))
      height: Math.max(implicitHeight, outputFlick.height - Style.space(20))
      text: root.text !== "" ? root.text : root.emptyText
      color: root.foregroundColor
      opacity: root.text !== "" ? 0.9 : 0.5
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      textFormat: TextEdit.PlainText
      wrapMode: TextEdit.WrapAnywhere
      readOnly: true
      selectByMouse: true
      selectByKeyboard: true
    }

  }

  Rectangle {
    anchors.right: parent.right
    anchors.rightMargin: Style.space(5)
    width: Style.space(3)
    height: Math.max(Style.space(24), outputFlick.height * outputFlick.height / outputFlick.contentHeight)
    y: outputFlick.y + (outputFlick.height - height) * outputFlick.contentY
      / Math.max(1, outputFlick.contentHeight - outputFlick.height)
    radius: width / 2
    color: root.foregroundColor
    opacity: outputFlick.contentHeight > outputFlick.height ? 0.3 : 0
  }
}
