import QtQuick

Item {
  id: root
  property bool enabled: false
  property string mode: "every-hours"
  property int interval: 6
  property string time: "03:00"
  property var weekdays: []

  signal changed()
}
