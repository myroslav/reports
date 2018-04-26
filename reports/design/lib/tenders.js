var jsp = require('./jsonpatch');
var startDate;
//global tender values
var kind;
var owner;
var tender_id;
var tender_status;
var tenderID;
var datemodified;
var emitter = {
    lot: function(lot, date, results) {
        results.push({
            key: [owner, date_normalize(date), lot.id],
            value: {
                tender: tender_id,
                lot: lot.id,
                value: lot.value.amount,
                currency: lot.value.currency,
                kind: kind,
                lot_status: lot.status,
                status: tender_status,
                datemodified: datemodified,
                startdate: startDate,
                tenderID: tenderID
            }
        });
    },
    tender: function(tender, date, results) {
        results.push({
            key: [owner, date_normalize(date)], 
            value: {
                tender: tender_id,
                value: tender.value.amount,
                currency: tender.value.currency,
                kind: kind,
                status: tender_status,
                datemodified: datemodified,
                startdate: startDate,
                tenderID: tenderID
            }
        });
    }
};

function find_first_revision_date(doc) {
    if ((typeof doc.revisions === 'undefined') || (doc.revisions.length === 0)) {
        return '';
    }
    return doc.revisions[0].date || '';
}

function count_lot_bids(lot, bids) {
    return ( bids || [] ).map(function(bid) {
        return ( bid.lotValues || [] ).filter(function(value) {
            return value.relatedLot === lot.id;
        }).length;
    }).reduce(function( total, curr) {
        return total + curr;
    }, 0) || 0;
}

function filter_bids(bids) {
    var min_date = Date.parse("2016-04-01T00:00:00+03:00");
    return bids.filter(function(bid) {
        var bid_date = Date.parse(bid.date);
        return (((bid.status || "invalid") === "active") && (+bid_date > +min_date));
    });
}

function count_lot_qualifications(qualifications, lot_id) {
    if ( (typeof qualifications === 'undefined') || (qualifications.length === 0) ) {
        return 0;
    }
    return qualifications.filter(function(qualification) {
        return qualification.lotID === lot_id;
    }).length;
}

function max_date(obj) { 
    //helper function to find max date in object 
    var dates = [];

    ['date', 'dateSigned', 'documents'].forEach(function(field){
        var date = obj[field] || '';
        if (date) {
            if (typeof date === "object") {
                date.forEach(function(d) {
                    dates.push(new Date(d.datePublished));
                });
            } else {
                dates.push(new Date(date));
            }
        }
    });
    return new Date(Math.max.apply(null, dates));
}

function date_normalize(date) {
    //return date in UTC format
    return ( (typeof date === 'object') ? date : (new Date(date)) ).toISOString().slice(0, 23);
}

function find_complaint_date(complaints) {
    return new Date(Math.max.apply(null, complaints.map(function(c) {
        var d = (c.type === 'claim') ? c.dateAnswered : c.dateDecision;
        if ( (typeof d === 'undefined') || (d === null) ) {
            return null;
        } else {
            return new Date(d);
        }
    }).filter(function(d) {
        return d !== null; 
    })));
}

function find_cancellation_max_date(cancellations) {
    if ((typeof cancellations === 'undefined') || (cancellations.length === 0)) {
        return null;
    }
    if (cancellations.length > 1) {
        return max_date(cancellations.reduce(function(prev_doc, curr_doc) {
            return ( prev_doc.date > curr_doc.date ) ? curr_doc : prev_doc;
        }));
    } else {
        return max_date(cancellations[0]);
    }
}

function find_awards_max_date(awards) {
    if ((typeof awards === 'undefined') || (awards.length === 0)) {
        return null;
    }
    var date = new Date(Math.max.apply(null, awards.map(function(aw) {
        if('complaints' in aw)  {
            var d = find_complaint_date(aw.complaints);
            if (isNaN(d.getTime())) {
                return new Date(aw.complaintPeriod.endDate);
            } else {
                return d;
            }
        } else {
            return new Date(aw.complaintPeriod.endDate);
        }
    })));
    return  date;
}

function Handler(tender) {
    this.status = tender.status;
    this.is_multilot = "lots" in tender;
    var bids_disclojure_date = (tender.qualificationPeriod || {}).startDate || (tender.awardPeriod || {}).startDate || null;
    this.bids_disclosure_standstill = new Date(bids_disclojure_date);
    if ('date' in tender) {
        if (['complete', 'cancelled', 'unsuccessful'].indexOf(tender.status) !== -1) {
            if (tender.status === 'cancelled') {
                if ((new Date(tender.date)) < this.bids_disclosure_standstill) {
                    this.tender_date = null;
                } else {
                    this.tender_date = new Date(tender.date);
                }
            } else {
                this.tender_date = new Date(tender.date);
            }
        } else {
            this.tender_date = null;
        }
    } else {
        switch (this.status) {
        case 'complete':
            this.tender_date = new Date( Math.max.apply(null, ( tender.contracts || [] ).filter(function(c) {
                return c.status === 'active';
            }).map(function(c){
                return max_date(c);
            })));
            break;
        case 'unsuccessful':
            this.tender_date = find_awards_max_date(tender.awards);
            break;
        case 'cancelled':
            var cancellation_date = find_cancellation_max_date(tender.cancellations.filter(function(cancellation) {
                return ( (cancellation.status === 'active') && (cancellation.cancellationOf === 'tender') );
            }));
            if (cancellation_date < this.bids_disclosure_standstill) {
                this.tender_date = null;
            } else {
                this.tender_date = cancellation_date;
            }
            break;
        default:
            this.tender_date = null;
        } }
};

function lotHandler(lot, tender){
    this.status = lot.status;
    this.tender_handler = new Handler(tender);
    if ('date' in lot) {
        if (['complete', 'cancelled', 'unsuccessful'].indexOf(lot.status) !== -1) {
            if (this.status === 'cancelled') {
                if ((new Date(lot.date)) < this.tender_handler.bids_disclosure_standstill) {
                    this.lot_date = null;
                } else {
                    this.lot_date = new Date(lot.date);
                }
            } else {
                this.lot_date = new Date(lot.date);
            }
        } else {
            if (this.tender_handler.status === 'cancelled') {
                this.lot_date = (this.tender_handler.tender_date !== null) ? this.tender_handler.tender_date : null;
            } else {
                this.lot_date = null;
            }
        }
    } else { 
        switch(this.status) {
        case 'unsuccessful':
            this.lot_date = find_awards_max_date((tender.awards || []).filter(function(award) {
                return award.lotID === lot.id;
            }));
            break;
        case 'cancelled':
            var lot_cancellation = find_cancellation_max_date((tender.cancellations || []).filter(function(cancellation) {
                return (cancellation.status === 'active') && (cancellation.cancellationOf === 'lot') && (cancellation.relatedLot === lot.id);
            }));
            if ((lot_cancellation !== null) && (lot_cancellation > this.tender_handler.bids_disclosure_standstill)) {
                this.lot_date = lot_cancellation;
            } else {
                this.lot_date = null;
            }
             break;
        case 'complete':

            var contract_date = '';
            tender.awards.forEach(function(award) {
                if (award.lotID === lot.id) {
                    (tender.contracts || []).forEach(function(contract) {
                        if (award.id === contract.awardID) {
                            if (contract.status === 'active') {
                               contract_date = max_date(contract);
                            }
                        }
                    });
                }
            });
            this.lot_date = contract_date || null;
            break;
        default:
            if (tender.status === 'cancelled') {
                if (this.tender_handler.tender_date !== null) {
                    if ( this.tender_handler.tender_date > this.tender_handler.bids_disclosure_standstill) {
                        this.lot_date = this.tender_handler.tender_date;
                    } else {
                        this.lot_date = null;
                    }
                } else {
                    this.lot_date = null;
                }
            } else {
                var lotDate = '';
                ( tender.awards || [] ).forEach(function(award) {
                    if (award.lotID === lot.id) {
                        (tender.contracts || []).forEach(function(contract) {
                            if (award.id === contract.awardID) {
                                if (contract.status === 'active') {
                                    lotDate = max_date(contract);
                                }
                            }
                        });
                    }
                });
                this.lot_date = lotDate || null;
            }
    } }
};

function check_lot(lot, tender) {

    var bids = filter_bids(tender.bids || []);

    switch (tender.procurementMethodType) {
        case 'competitiveDialogueUA.stage2':
        case 'aboveThresholdUA':
            if (count_lot_bids(lot, bids) > 1) {
                return true; 
            }
            break;
        case 'competitiveDialogueEU.stage2':
        case 'aboveThresholdEU':
            if (count_lot_qualifications((tender.qualifications || []), lot.id) > 1) {
                return true; 
            }
            break;
        case 'competitiveDialogueUA':
        case 'competitiveDialogueEU':
            if (count_lot_qualifications((tender.qualifications || []), lot.id) > 2) {
                return true;
            }
            break;
        case 'aboveThresholdUA.defense':
            var lot_awards = ('awards' in tender) ? (
                tender.awards.filter(function(a) {
                    return a.lotID === lot.id;
                })
            ) : [];
            if ((count_lot_bids(lot, bids) < 2 ) && (lot_awards.length === 0)) {
                return false;
            } else {
                if (count_lot_bids(lot, bids) > 0) {
                    return true;
                }
            }
            break;
        default:
            if (count_lot_bids(lot, bids) > 0) {
                return true; 
            }
    }
    return false;
}

function check_tender(tender) {
    switch (tender.procurementMethodType) {
        case 'competitiveDialogueUA.stage2':
        case 'aboveThresholdUA':
            if (tender.numberOfBids > 1) {
                return true;
            }
            break;
        case 'competitiveDialogueEU.stage2':
        case 'aboveThresholdEU':
            if (((tender.qualifications || []).length) > 1) {
                return true;
            }
            break;
        case 'aboveThresholdUA.defense':
            if( (tender.numberOfBids < 2) && !('awards' in tender)) {
                return false;
            } else {
                if (tender.numberOfBids > 0) {
                    return true;
                }
            }
            break;
        case 'competitiveDialogueUA':
        case 'competitiveDialogueEU':
            if (((tender.qualifications || []).length) > 2) {
                return true;
            }
            break;
        default:
            if (tender.numberOfBids > 0) {
                return true;
            }
            return false;
    }
    return false;
}

function get_contract_date(tender) {
    var date = '';
    (tender.contracts || []).forEach(function(contract) {
        if (contract.status === 'active') {
            date = contract.date;
        }
    });
    return date;
}

function get_contract_date_for_lot(tender, lot) {
    var date = '';
    (tender.contracts || []).forEach(function(contract) {
        var award_id = contract.awardID;
        if (contract.status === 'active') {
            (tender.awards || []).forEach(function(award) {
                if (award_id === award.id) {
                    if (award.lotID === lot.id) {
                        date = contract.date;
                    }
                }
            });
        }
    });
    return date;
}

function find_date_from_revisions(original_tender, lot) {
    var date = 'date';
    active_awards = original_tender.awards.filter(function(award) {
        return ((award.status === "active") && (typeof lot !== "undefined" ? award.lotID === lot.id : true));
    });
    if (active_awards.length > 0) {
        date = active_awards[0].date;
    }
    var revs = original_tender.revisions.slice().reverse().slice(0, original_tender.revisions.length - 1);
    var tender = JSON.parse(JSON.stringify(original_tender));
    for (var i = 0; i < revs.length; i++) {
        var prev = jsp.apply(tender, revs[i].changes);
        if (!('awards' in prev)) {
            break;
        } else {
            for (var j = 0; j < prev.awards.length; j++) {
                if ((prev.awards[j].status === 'active') && (typeof lot !== "undefined" ? prev.awards[j].lotID === lot.id : true)) {
                    date = (date > prev.awards[j].date) ? prev.awards[j].date : date;
                }
            }
        }
    }
    if (date !== 'date') {
        return date;
    }
};

function get_first_award_date(tender, lot) {
    var non_unsuccessful_aw = ( tender.awards  || [] ).filter(function(awd) {
        return (['unsuccessful', 'pending'].indexOf(awd.status) === -1);
    });
    
    if (typeof lot !== "undefined") {
        non_unsuccessful_aw = non_unsuccessful_aw.filter(function(award) {
            return (award.lotID === lot.id);
        });
    }

    if (non_unsuccessful_aw.length > 0) {
        if (non_unsuccessful_aw[0].status === 'cancelled') {
            return find_date_from_revisions(tender);
        }
        else {
            return non_unsuccessful_aw[0].date;
        }
    } else {
        return null;
    }
}

function tender_date_new_alg(tender) {
    var type = tender.procurementMethodType;
    if ('belowThreshold' === type) {
        return get_first_award_date(tender);
    } else {
        return get_contract_date(tender);
    }
}

function lot_date_new_alg(tender, lot) {
    var type = tender.procurementMethodType;
    if ('belowThreshold' === type) {
        return get_first_award_date(tender, lot);
    } else {
        return get_contract_date_for_lot(tender, lot);
    }
}

function find_tender_data (tender, results) {
    var new_alg_date = '2017-08-16T00:00:01';
    if (startDate < new_alg_date) {
        var handler = new Handler(tender);
        if (handler.is_multilot) {
            tender.lots.forEach(function(lot){
                if (check_lot(lot, tender)) {
                    var lot_handler = new lotHandler(lot, tender);
                    if (lot_handler.lot_date !== null) {
                        emitter.lot(lot, lot_handler.lot_date, results);
                    }
                }
            });

        } else {

            if (check_tender(tender)) {
                if (tender.status === 'cancelled') {
                    if (handler.tender_date < handler.bids_disclosure_standstill) { return; }
                }
                if (handler.tender_date !==  null) {
                    emitter.tender(tender, handler.tender_date, results);
                }
            }
        }
    } else {
        if ('lots' in tender) {
            tender.lots.forEach(function(lot) {
                var date_opened = lot_date_new_alg(tender, lot);
                if (date_opened) {
                    emitter.lot(lot, date_opened, results);
                }
            });
        } else {
            var date_opened = tender_date_new_alg(tender);
            if (date_opened) {
                emitter.tender(tender, date_opened, results);
            }
        }
    }
}

function main(doc) {
    if (doc.doc_type !== "Tender") {return;}

    if (doc.procurementMethodType === 'esco') { return []; }
    startDate = (doc.enquiryPeriod || {}).startDate;
    //tender checks
    if ( !startDate ) {
        startDate = find_first_revision_date(doc);
    }

    // only first stage is completed
    if (['competitiveDialogueEU', 'competitiveDialogueUA'].indexOf(doc.procurementMethodType) !== -1) {
        if (['unsuccessful', 'cancelled'].indexOf(doc.status) === -1) {
            return [];
        }
    }

    if ((!startDate) || (startDate < "2016-04-01")) {return;}
    if (doc.procurementMethod !== "open") {
        if (doc.procurementMethodType.indexOf('stage2') !== -1) {
            if (doc.procurementMethod !== 'selective') {
                return [];
            } 
        } else {
            return [];
        }
    }
    if ((doc.mode || "") === "test") {
        return [];
    }

    bids_disclojure_date = (doc.qualificationPeriod || {}).startDate || (doc.awardPeriod || {}).startDate || null;
    if (!bids_disclojure_date) {
        return [];
    }

    //global tender values
    kind = doc.procuringEntity.kind || "_kind";
    owner = doc.owner;
    tender_id = doc._id;
    tender_status = doc.status;
    tenderID = doc.tenderID;
    datemodified = doc.dateModified;

    var results = [];
    find_tender_data(doc, results);
    return results;
}

exports.main = main;
exports.find_first_revision_date = find_first_revision_date;
exports.count_lot_bids = count_lot_bids;
exports.filter_bids = filter_bids;
exports.count_lot_qualifications = count_lot_qualifications;
exports.max_date = max_date;
exports.find_complaint_date = find_complaint_date;
exports.find_cancellation_max_date = find_cancellation_max_date;
exports.find_awards_max_date = find_awards_max_date;
exports.Handler = Handler;
exports.lotHandler = lotHandler;
exports.check_lot = check_lot;
exports.check_tender = check_tender;
exports.get_contract_date = get_contract_date;
exports.get_contract_date_for_lot = get_contract_date_for_lot;
exports.find_date_from_revisions = find_date_from_revisions;
exports.get_first_award_date = get_first_award_date;
