function(doc) {
    
    // tender checks
    if (doc.doc_type !== "Tender") {return;}
    var startDate = (doc.enquiryPeriod||{}).startDate;
    if (!startDate) {
        startDate = find_first_revision_date(doc);
    }
    if (['competitiveDialogueEU', 'competitiveDialogueUA'].indexOf(doc.procurementMethodType) !== -1) {
      if (['open', 'selective'].indexOf(doc.procurementMethod) !== -1) {return;}
    } else {
      if (doc.procurementMethod !== "open") {return;}
    }
    if ((doc.mode || "") === "test") { return;}

    var bids_disclojure_date = (doc.qualificationPeriod || {}).startDate || (doc.awardPeriod || {}).startDate || null;
    if(!bids_disclojure_date) { return; }

    // payments should be calculated only from first stage of CD and only once
    if (['competitiveDialogueEU.stage2', 'competitiveDialogueUA.stage2'].indexOf(doc.procurementMethodType) !== -1) {
        log('Skipping tender stage2 ' + doc._id);
        return;
    }

    var id = doc._id;
    var tender_start_date = doc.tenderPeriod.startDate;
    var tenderID = doc.tenderID;
    var is_multilot = ("lots" in doc) ? true:false;
    var type = doc.procurementMethodType;

    function get_eu_tender_bids(tender) {
        var qualified_bids = (tender.qualifications || []).map(function(qualification) {
            return qualification.bidID;
        });
        return (tender.bids || []).filter(function(bid) {
            return (qualified_bids.indexOf(bid.id) !== -1);
        });
    }

    function filter_bids(bids) {
        var min_date =  Date.parse("2016-04-01T00:00:00+03:00");
        return bids.filter(function(bid) {
            var bid_date =  Date.parse(bid.date);
            return (((bid.status || "invalid") === "active") && (+bid_date > +min_date));
        });
    }

    function find_first_revision_date(doc) {
        if ((typeof doc.revisions === 'undefined') || (doc.revisions.length === 0)) {
            return '';
        }
        return doc.revisions[0].date || '';
    }

    function date_normalize(date) {
        //return date in UTC format
        return  ((typeof date !== 'object')?(new Date(date)):date).toISOString().slice(0, 23);
    }

    function get_bids(tender) {
        switch (tender.procurementMethodType) {
            case 'aboveThresholdEU':
            case 'competitiveDialogueEU':
            case 'competitiveDialogueUA':
                return get_eu_tender_bids(tender);
            default:
                return filter_bids(tender.bids || []);
        }
    }

    function count_lot_bids(lot, tender) {
        var bids = get_bids(tender);
        return bids.map(function(bid) {
            return ( bid.lotValues || [] ).filter(function(value) {
                return value.relatedLot === lot.id;
            }).length;
        }).reduce(function( total, curr) {
            return total + curr;
        }, 0);
    }

     function count_lot_qualifications(qualifications, lot_id) {
        if ( (typeof qualifications === 'undefined') || (qualifications.length === 0) ) {
            return 0;
        }
        return qualifications.filter(function(qualification) {
            return qualification.lotID === lot_id;
        }).length;
    }

    function check_tender_bids(tender) {
        var type = tender.procurementMethodType;
        switch (type) {
            case 'aboveThresholdUA':
                if (tender.numberOfBids < 2) {
                    return false;
                }
                return true;
            case 'aboveThresholdEU':
                if ((tender.qualifications || []).length < 2) {
                    return false;
                }
                return true;
            case 'aboveThresholdUA.defense':
                if ((tender.numberOfBids < 2) && !('awards' in tender)) {
                    return false;
                }
                return true;
            case 'competitiveDialogueEU':
            case 'competitiveDialogueUA':
                if ((tender.qualifications || []).length < 3) {
                    return false;
                }
                return true;
            default:
                return true;
        }
    }

    function check_lot_bids(tender, lot) {
        var type = tender.procurementMethodType;
        switch (type) {
        case 'aboveThresholdUA':
            if (count_lot_bids(lot, tender) < 2) {
                return false;
            }
            return true;
        case 'aboveThresholdEU':
            if (count_lot_qualifications(tender.qualifications, lot.id) < 2) {
                return false;
            }
            return true;
        case 'aboveThresholdUA.defense':
            var lot_awards = ('awards' in tender) ? (
                tender.awards.filter(function(a) {
                    return a.lotID === lot.id;
                })
            ) : [];
            if (((count_lot_bids(lot, tender) < 2) && (lot_awards.length === 0))) {
                return false;
            }
            return true;
        case 'competitiveDialogueEU':
        case 'competitiveDialogueUA':
            if (count_lot_qualifications(tender.qualifications, lot.id) < 3) {
                return false;
            }
            return true;
        default:
            return true;
        }
    }

    function check_tender(tender) {
        switch(tender.status) {
        case "cancelled":
            if ((new Date(tender.date)) < (new Date(bids_disclojure_date))) {
                return false;
            }
            if (! check_tender_bids(tender)) {
                return false;
            }
            return true;
        case "unsuccessful":
            if (! check_tender_bids(tender)) {
                return false;
            }
            return true;
        default:
            return true;
        }
    }

    function check_lot(tender, lot){
        switch (lot.status) {
        case "cancelled":
                if ((new Date(lot.date)) < (new Date(bids_disclojure_date))) {
                    return false;
                }
            if (! check_lot_bids(tender, lot)) {
                return false;
            }
            return true;
        case "unsuccessful":
            if (! check_lot_bids(tender, lot)) {
                return false;
            }
            return true;
        default:
            return true;
        }
    }

    var emitter = {
        lot: function(owner, date, bid, lot, audits) {
            emit([owner, date, bid.id, lot.id], {
                tender: id,
                lot: lot.id,
                value: lot.value.amount,
                currency: lot.value.currency,
                bid: bid.id,
                startdate: startDate,
                audits: audits,
                tender_start_date: tender_start_date,
                cancelled: lot.status === 'cancelled',
                tenderID: tenderID
            });
        },
        tender: function(owner, date, bid, tender, audits){
            emit([owner, date, bid.id], {
                tender: id,
                value: tender.value.amount,
                currency: tender.value.currency,
                bid: bid.id,
                audits: audits,
                startdate: startDate,
                cancelled: tender.status === 'cancelled',
                tender_start_date: tender_start_date,
                tenderID: tenderID
            });
        }
    };

  
    function find_audit(tender, lot) {
        var pattern = (typeof lot === 'undefined' || lot === {}) ? 'audit' : 'audit_' + tender._id + '_' + lot.id;
        var audits = (tender.documents || []).filter(function(doc) {
            return doc.title.match(pattern);
        });
        return (audits.length > 1) ? audits.reduce(function(prev_doc, curr_doc) {
          return (prev_doc.dateModified || '') > (curr_doc.dateModified || '') ? curr_doc : prev_doc;
        }) : audits[0];
    }

    function emit_results(tender) {

      var bids = get_bids(tender);

      if(is_multilot) {
        (bids || []).forEach(function(bid) {
          bid.lotValues.forEach(function(value) {
            tender.lots.forEach(function(lot) {
              if (check_lot(tender, lot)) {
                if (value.relatedLot === lot.id) {
                  var audit = find_audit(tender, lot);
                  emitter.lot(bid.owner, date_normalize(bids_disclojure_date), bid, lot, audit);
                }
              }
            });
          });
        });
      } else {
        if (!(check_tender(tender))) { return; }
        var audit = find_audit(tender, {});
        (bids || []).forEach(function(bid) {
          emitter.tender(bid.owner, date_normalize(bids_disclojure_date), bid, tender, audit);
        });
      }
    }
    emit_results(doc);
}
