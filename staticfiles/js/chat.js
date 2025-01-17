function ChatController() {
    return function (scope, http, httpParamSerializerJQLike, timeout, interval, sce) {

        var start_polling = false;

        scope.show_load_previous = false;
        scope.messages = [];
        scope.message = '';
        scope.uploadFile = null;
        scope.load_message_interval = null;
        scope.audio_blob = null;

        scope.$on('startChat', function (event, arg) {
            scope.load_messages();
        });

        scope.$on('stopChat', function (event, arg) {
            interval.cancel(scope.load_message_interval);
            start_polling = false;
            scope.messages = [];
            scope.show_load_previous = false;
            scope.message = '';
            scope.uploadFile = null;
        });

        var get_user_id_queryset = function () {
            if (scope.user_id === undefined) {
                return ""
            }
            else {
                return '&user=' + scope.user_id;
            }
        };

        var escapeHTML = function(text) {
            var map = {
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
        
            return text.replace(/<\/?(?!br|a|\/a)[^>]+>/g, function (tag) {
                return tag.replace(/[<>]/g, function (m) { return map[m]; });
            });
        }

        var handle_messages = function (response) {
            let firstId = 0;
            if (scope.messages.length > 0) {
                firstId = scope.messages[0].id;
            }

            if (response.messages.length == 0) {
                return;
            }

            let newMessages = response.messages;
            newMessages.forEach(function (message) {
                message['time_display'] = moment(message.time).format("H:mm");
                message['day_display'] = moment(message.time).calendar({sameDay: '[Today]', lastDay: '[Yesterday]', lastWeek: 'DD/MM/YYYY', sameElse: 'DD/MM/YYYY'});
                message['msg'] = sce.trustAsHtml(escapeHTML(message['msg']));
                let existMessage = scope.messages.find(element => element.id === message.id);
                if (existMessage === undefined) {
                    scope.messages.push(message);
                }
            });

            scope.messages.sort(function (a, b) {
                return a.id - b.id;
            });

            scope.show_load_previous = true;

            if (scope.messages[0].id >= firstId) {
                timeout(function () {
                    window.scrollTo(0, document.body.scrollHeight);
                    let msgHistory = $('.msgs-content');
                    msgHistory.scrollTop(msgHistory.prop('scrollHeight'));
                }, 100);
            }
        };

        scope.message_key_press = function(keyEvent) {
            var isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
            if (keyEvent.which == 13 && !keyEvent.shiftKey && !isMobile) {
                scope.send_message();
                keyEvent.preventDefault();
            }
        };

        scope.send_message = function () {
            const url = chatApi + '?send_message=1';
            var data = new FormData();
            data.append('msg', scope.message);
            if (scope.user_id !== undefined) {
                data.append('user_id', scope.user_id)
            }
            if (scope.uploadFile) {
                data.append('file', scope.uploadFile);
            }

            if (scope.audio_blob) {
                data.append('audio_file', scope.audio_blob);
            }

            scope.messages.forEach(x => {
               if (x.r) {
                   x.read = true;
               }
            });
            scope.message = '';
            scope.clear_file();
            scope.clear_record();
            http({
                url: url,
                method: 'POST',
                data: data,
                headers: {
                    'Content-Type': undefined
                }
            }).then(function (response) {
                console.log("message sent");
                handle_messages(response.data);
            }, function (error) {
                console.log(error);
            });
        };

        scope.clear_file = function () {
            scope.uploadFile = null;
            $("input.inputfile").val(null);
        };

        scope.get_attachment_url = function(msg_id) {
            return chatApi + '?attachment_id=' + msg_id
        };

        scope.load_messages = function (previous, next) {
            if (previous == null && next == null) {
                if (scope.user_id !== undefined) {
                    $(".inputfile").next("label").css("visibility", "visible");
                }
                let url = chatApi + '?receive_message=1' + get_user_id_queryset();
                http({
                    url: url,
                    method: 'GET'
                }).then(function (response) {
                    handle_messages(response.data);
                    if (start_polling == false) {
                        start_polling = true;
                        scope.load_message_interval = interval(function () {
                            if (start_polling == true) {
                                scope.load_messages(null, 1);
                            }
                        }, 3000);
                    }
                });
            } else if (previous != null) {
                let first_id = scope.messages[0].id;
                let url = chatApi + '?receive_message=1' + get_user_id_queryset() + '&prev=' + first_id;
                scope.show_load_previous = false;
                http.get(url).then(function (response) {
                    handle_messages(response.data);
                });
            } else if (next != null) {
                let url = chatApi + '?receive_message=1' + get_user_id_queryset();
                if (scope.messages.length > 0) {
                    let last_id = scope.messages[scope.messages.length - 1].id;
                    url = url + '&next=' + last_id;
                }
                http.get(url).then(function (response) {
                    handle_messages(response.data);
                });
            }
        };

        var gumStream;
        var AudioContext = window.AudioContext || window.webkitAudioContext;
        var input;
        scope.rec = null;
        scope.is_recording = false;

        scope.clear_record = function() {
            if (scope.rec) {
                let chatInput = $(".chat-input-text");
                chatInput.prop( "disabled", false );
            }
            scope.rec = null;
            scope.audio_blob = null;
        };

        var setTimeLeft = function() {
            if (scope.is_recording) {
                timeout(function () {
                    setTimeLeft();
                }, 200);
                if (scope.rec.recordingTime()) {
                    $(".recording-time-left").text(Math.ceil(scope.rec.recordingTime()).toString() + "/" + scope.rec.options.timeLimit.toString());
                }
            }
        };

        scope.start_recording = function () {
            scope.is_recording = true;
            scope.audio_blob = null;
            scope.uploadFile = null;
            let chatInput = $(".chat-input-text");
            chatInput.val('');
            chatInput.prop( "disabled", true );
            if (scope.rec) {
                scope.rec = null;
            }
            var constraints = {audio: true, video: false};
            navigator.mediaDevices.getUserMedia(constraints).then(function (stream) {
                audioContext = new AudioContext();
                gumStream = stream;
                input = audioContext.createMediaStreamSource(stream);
                scope.rec = new WebAudioRecorder(input, {
                    workerDir: "/static/static/js/",
                    encoding: 'mp3',
                    onEncoderLoading: function(recorder, encoding) {
                        // show "loading encoder..." display
                        console.log("Loading " + encoding + " encoder...");
                    },
                    onEncoderLoaded: function(recorder, encoding) {
                        // hide "loading encoder..." display
                        console.log(encoding + " encoder loaded");
                    }
                });
                scope.rec.onComplete = function(recorder, blob) {
                    scope.is_recording = false
                    console.log("Encoding complete");
                    createDownloadLink(blob);
                }
                scope.rec.setOptions({
                    timeLimit: 30,
                    encodeAfterRecord: true,
                    mp3: {
                        bitRate: 80
                    }
                });

                scope.rec.startRecording();
                console.log("Recording started");
                setTimeLeft();
            }).catch(function(err) {

            });
        };

        var createDownloadLink = function (blob) {
            var url = URL.createObjectURL(blob);
            scope.audio_blob = blob;
            var au = $("audio.audio-controller");
            au.attr('src', url);
        };

        scope.stop_recording = function () {
             console.log("stopRecording() called");
            //stop microphone access
            gumStream.getAudioTracks()[0].stop();
            //tell the recorder to finish the recording (stop recording + encode the recorded audio)
            scope.rec.finishRecording();
            console.log('Recording stopped');
        };

    }

}

function FileModelDirective() {
    return function (parse) {
        return {
            restrict: 'A', //the directive can be used as an attribute only

            /*
             link is a function that defines functionality of directive
             scope: scope associated with the element
             element: element on which this directive used
             attrs: key value pair of element attributes
             */
            link: function (scope, element, attrs) {
                var model = parse(attrs.fileModel),
                    modelSetter = model.assign; //define a setter for demoFileModel

                //Bind change event on the element
                element.bind('change', function () {
                    //Call apply on scope, it checks for value changes and reflect them on UI
                    scope.$apply(function () {
                        //set the model value
                        modelSetter(scope, element[0].files[0]);
                    });
                });
            }
        };
    };
}

function FixAudioSrcDirective() {
    return function () {
        return {
            restrict: 'A',
            link: function (scope, element, attrs) {
                attrs.$set('src', attrs.vsrc);
            }
        }

    }
}