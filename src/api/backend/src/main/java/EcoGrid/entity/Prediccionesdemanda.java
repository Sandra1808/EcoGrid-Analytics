package EcoGrid.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "PREDICCIONESDEMANDA")
public class Prediccionesdemanda {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDPREDICCION", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDTIEMPO", nullable = false)
    private Tiempohorario idtiempo;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDMODELO", nullable = false)
    private Modelosml idmodelo;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDCCAA", nullable = false)
    private Comunidadautonoma idccaa;

    @Column(name = "DEMANDAPREDICHAMW", precision = 12, scale = 4)
    private BigDecimal demandapredichamw;

    @Column(name = "DEMANDABASELINEMW", precision = 12, scale = 4)
    private BigDecimal demandabaselinemw;

    @ColumnDefault("CURRENT_TIMESTAMP")
    @Column(name = "FECHA")
    private Instant fecha;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Tiempohorario getIdtiempo() {
        return idtiempo;
    }

    public void setIdtiempo(Tiempohorario idtiempo) {
        this.idtiempo = idtiempo;
    }

    public Modelosml getIdmodelo() {
        return idmodelo;
    }

    public void setIdmodelo(Modelosml idmodelo) {
        this.idmodelo = idmodelo;
    }

    public Comunidadautonoma getIdccaa() {
        return idccaa;
    }

    public void setIdccaa(Comunidadautonoma idccaa) {
        this.idccaa = idccaa;
    }

    public BigDecimal getDemandapredichamw() {
        return demandapredichamw;
    }

    public void setDemandapredichamw(BigDecimal demandapredichamw) {
        this.demandapredichamw = demandapredichamw;
    }

    public BigDecimal getDemandabaselinemw() {
        return demandabaselinemw;
    }

    public void setDemandabaselinemw(BigDecimal demandabaselinemw) {
        this.demandabaselinemw = demandabaselinemw;
    }

    public Instant getFecha() {
        return fecha;
    }

    public void setFecha(Instant fecha) {
        this.fecha = fecha;
    }

}