import QtQuick

Item {
  id: root
  property string text: ""

  Flickable {
    anchors.fill: parent
    contentWidth: width
    contentHeight: log.implicitHeight

    Text {
      id: log
      width: parent.width
      text: root.text
      wrapMode: Text.WrapAnywhere
    }
  }
}
